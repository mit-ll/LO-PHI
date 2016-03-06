"""
    This file contains all of the code for the local controller for LO-PHI
    This code accepts a connection on a TCP socket and allows the starting and
    stopping of LO-PHI configs.  This controller also handles the load on the 
    VMs and loads in all of the static configurations.  For large-scale 
    experiments, this will be actuated by the puppet master.

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import sys
import multiprocessing
import threading
import socket
import time
import os

import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.network as NET
from lophi.machine.virtual import VirtualMachine

# LO-PHI Automation
import lophi_automation.configs.helper as Configs
import lophi_automation.protobuf.helper as ProtoBuf
from lophi_automation.analysis import LoPhiAnalysisEngine
from lophi_automation.network.command import LophiCommand

# Globals
import lophi.globals as  G

# Append our directory so we can import from there
SCRIPTS_TMP_PATH = os.path.join(G.DIR_ROOT,G.DIR_TMP)
sys.path.append(SCRIPTS_TMP_PATH)

ANALYSIS_STATUS = multiprocessing.Manager().dict() 
ANALYSIS_QUEUED = multiprocessing.Manager().list() 
ANALYSIS_RUNNING = multiprocessing.Manager().list()
ANALYSIS_STATUS['queued'] = ANALYSIS_QUEUED
ANALYSIS_STATUS['running'] = ANALYSIS_RUNNING
SERVICES_HOST = None


class LophiScheduler(multiprocessing.Process):
    """
        This is our scheduler for assigning analysis to machines
        
        The idea is to run one for each type of machine that we have
        E.g. Physical and Virtual
    """
    
    ANALYSIS_DICT = {}
    
    def __init__(self, machine_list, machine_queue):
        
        self.machine_list = machine_list
        self.machine_queue = machine_queue
        self.analysis_queue = multiprocessing.Queue()
        
        multiprocessing.Process.__init__(self)

    def _cleanup_pointers(self):
        """
            We keep a reference from analysis id -> analysis object
            This will clean up any references that 
        """
        logger.debug("Cleaning up pointers.")
        
        rem = []
        for aid in self.ANALYSIS_DICT:
            if aid not in ANALYSIS_QUEUED and aid not in ANALYSIS_RUNNING:
                rem.append(aid)
                
        for aid in rem:
            logger.debug("Cleaning up analysis %d."%aid)
            analysis = self.ANALYSIS_DICT.pop(aid)
            del analysis

    def queue_analysis(self, analysis_tuple):
        """
            Nice interface to queue a new analysis
        """
        
        # Send to our queue
        self.analysis_queue.put(analysis_tuple)
        
    def load_analysis(self,tmp_name_file):
        
        tmp_name = os.path.basename(tmp_name_file).split(".")[0]
        AnalysisClass = None
        
        try:
            import importlib
            Analysis = importlib.import_module(tmp_name)
            
            os.remove(tmp_name_file)
            os.remove(tmp_name_file+"c")

            AnalysisClass = Configs.extract_analysis(Analysis)
        except:
            G.print_traceback()
            logger.error("Could not import received file.")
        
        return AnalysisClass

    def run(self):
        logger.info("Started LO-PHI analysis scheduler. (PID: %d)"%os.getpid())
        
        # Loop forever, consuming analyses and assigning machines to them
        while True:
            
            # Cleanup any previous analysis
            self._cleanup_pointers()
            
            # Get an analysis
            (analysis_file, command) = self.analysis_queue.get()

            # Initialize our analysis
            AnalysisClass = self.load_analysis(analysis_file)
            analysis = LoPhiAnalysisEngine(running_dict=ANALYSIS_STATUS,
                                           services_host=SERVICES_HOST)
            
            ANALYSIS_QUEUED.append(analysis.id)
            
            if command.machine is None:
            
                logger.debug("Got Analysis: %s"%AnalysisClass)
                
                machine_name =  self.machine_queue.get()
                machine = self.machine_list[machine_name]
            
                logger.debug("Got Machine: %s"%machine)
                analysis.start(AnalysisClass,
                                    lophi_command=command,
                                    machine_name=machine_name,
                                    machine_list=self.machine_list,
                                    machine_queue=self.machine_queue)
            else:
                logger.debug("Got Machine: %s"%command.machine)
                
                # Did the user define a machine?
                machine_name = command.machine
                if machine_name in self.machine_list.keys():
                    # Get our machine
                    machine = self.machine_list[machine_name]
                    if machine.ALLOCATED >= 0:
                        logger.warning("Machine (%s) is already allocated to %d."%(machine.config.name,machine.ALLOCATED))
                
                # Check to see if a vm with this name exists
                elif command.machine_type != G.MACHINE_TYPES.PHYSICAL:
                    
                    # Init a VM object
                    vm = VirtualMachine(command.machine,command.machine_type)
                    if vm.power_status() == G.SENSOR_CONTROL.POWER_STATUS.UNKNOWN:
                        logger.error("Virtual machine (%s) does not exist."%command.machine)
                        return False
                    else:
                        machine = vm
                else:
                    logger.error("Could not find machine: %s"%machine_name)
                    return False
            
                analysis.start(AnalysisClass,
                                    lophi_command=command,
                                    machine=machine)
    
            # Update our dict
            # This is neccesary to keep a pointer to the analysis so that the 
            # scheduler won't kill the thread
            self.ANALYSIS_DICT.update({analysis.id: analysis})

            # Print some status
            print "* Starting analysis (%s) on machine (%s)."%(AnalysisClass.NAME,
                                                                    machine.config.name)
            
            time.sleep(1)



class LoPhiController(multiprocessing.Process):
    """
        The controller is in charge of importing all of the configurations, 
        controlling all of the SUA threads, and aggregating all of their 
        outputs.  This will then listen on a socket for commands that can 
        control all of the SUA's including their Xen images.
    """
    # List of our running engines    
    
    LISTS = {'machines',
             'analysis'}

    ANALYSIS_DICT = {}

    def __init__(self, options, positionals):
        """
            Initialize our controller.  This includes initializing all of the 
            configurations and opening all of the appropriate logfiles.
        """

        # Set our port to bind to
        self._sock = None
        self.PORT_NUM = options.port

        # AMQP Host (Only used to hand off to analysis
        self.services_host = options.services_host

        # What config file are we loading?
        sensor_config_file = options.sensor_config_file

        # What config file are we loading?
        machine_config_file = options.machine_config_file
        
        # Disk images config file
        images_config_file = options.images_config_file

        # Import our available sensors
        logger.debug("Importing sensor config file (%s)"%sensor_config_file)
        self.sensor_list = Configs.import_from_config(sensor_config_file, "sensor")
        
        # Import our available machines
        logger.debug("Importing machine config file (%s)"%machine_config_file)
        self.machine_list = Configs.import_from_config(machine_config_file, "machine")

        # Import our image mappings
        logger.debug("Importing images config file (%s)"%images_config_file)
        self.images_map = Configs.import_from_config(images_config_file, "images")


        # Provision the number of requested VMs
        print "* Initializing %d virtual machines..."%options.vm_count
        for x in range(0,options.vm_count):
            tmp_name = "lophi-%d"%x
            self.machine_list[tmp_name] = VirtualMachine(tmp_name,force_new=True)


        # Build our dictionary of queues
        # This queues are handed to analysis for scheduling
        self.MACHINE_QUEUES = {}
        
        self.ANALYSIS_SCHEDULER = {}

        print "* Assigning sensors to machines, and configure machines"
        for m in self.machine_list:
            
            # Setup their image maps
            self.machine_list[m].add_image_map( \
                 self.images_map[self.machine_list[m].type])
            
            
            # Add sensors and PXE server to physical machines    
            if self.machine_list[m].type == G.MACHINE_TYPES.PHYSICAL:
                # Add sensors
                self.machine_list[m].add_sensors(self.sensor_list)
                # Add pxe_server
                from lophinet.pxeserver import PXEServer
                pxe_server = PXEServer(options.pxe_server)
                self.machine_list[m].add_pxe_server(pxe_server)
                
        manager = multiprocessing.Manager()
        for m in self.machine_list:
            # Get our indices
            t = self.machine_list[m].type
            # New queue?
            if t not in self.MACHINE_QUEUES:
                machine_queue = manager.Queue()
                self.MACHINE_QUEUES[t] = machine_queue 
                self.ANALYSIS_SCHEDULER[t] = LophiScheduler(self.machine_list,
                                                            machine_queue)
                self.ANALYSIS_SCHEDULER[t].start()
            # Add to queue
            self.MACHINE_QUEUES[t].put(m)

        

        
        # Ensure that we can share this list with our analysis threads        
#         self.machine_list = multiprocessing.Manager().dict(self.machine_list)
            
        # Setup our FTP info
        self.ftp_ip_physical = self.ftp_ip_virtual = None
        try:
            self.ftp_ip_physical = NET.get_ip_address(options.ftp_physical)
        except:
            logger.error("Could not find ip for physical FTP interface. (%s)"%
                         options.ftp_physical)
        try:
            self.ftp_ip_virtual = NET.get_ip_address(options.ftp_virtual)
        except:
            logger.error("Could not find ip for virtual FTP interface. (%s)"%
                         options.ftp_virtual)
            
        # Server stuff
        self.RUNNING = True
        
        # Init our multiprocess
        multiprocessing.Process.__init__(self)
        
        """ 
            @TODO: Should we do anything to initialize machines?  
                    E.g. power them all off?
        """
        

    def __del__(self):
        """ Try to clean up everything nicely """
        
        # Clean up our socket    
        try:
            self._sock.close()
        except:
            pass
        
        # clean up our running analysis
        for a in self.ANALYSIS_DICT:
            self.ANALYSIS_DICT[a].stop()
            
        for a in self.ANALYSIS_SCHEDULER:
            self.ANALYSIS_SCHEDULER[a].terminate()
            
#     def _cleanup_pointers(self):
#         """
#             We keep a reference from analysis id -> analysis object
#             This will clean up any references that 
#         """
#         logger.debug("Cleaning up pointers.")
#         
#         rem = []
#         for aid in self.ANALYSIS_DICT:
#             if aid not in ANALYSIS_QUEUED and aid not in ANALYSIS_RUNNING:
#                 rem.append(aid)
#                 
#         for aid in rem:
#             logger.debug("Removing %d"%aid)
#             del self.ANALYSIS_DICT[aid]

   
    def _get_analysis(self,sock):
        """
            Download and import our analysis class
            
            @param sock: Socket to download analysis file from
            @return: Subclass of LophiAnalysis downloaded from the network to 
                        be used for analysis 
        """
        # Get our script to execute
        script = G.read_socket_data(sock)
            
        # generate a temporary filename to store this script
        import random
        import string
        tmp_name = ''.join(random.choice(string.ascii_uppercase) for x in range(10))
        tmp_name_file = os.path.join(SCRIPTS_TMP_PATH, tmp_name + ".py")
        try:
            
            
            logger.debug("Creating tmp file: %s"%tmp_name_file)
            # Import our script so that we can use it
            f = open(tmp_name_file,"w+")
            f.write(script)
            f.close()
        except:
            logger.error("Could not create temporary script file.")
            
        return tmp_name_file
    
   
    def analysis_stop(self,aid):
        """
            Stop a given analysis
        """
        print "* Stopping analysis (%d)."%aid
        if aid in self.ANALYSIS_DICT:
            print self.ANALYSIS_DICT[aid]
            self.ANALYSIS_DICT[aid].stop()
            return True
        else:
            logger.error("Analysis with ID %d not found."%aid)
            return False
        
   
    def analysis_pause(self,aid):
        """
            Pause a given analysis
        """
        print "* Pausing analysis (%d)."%aid
        if aid in self.ANALYSIS_DICT:
            self.ANALYSIS_DICT[aid].pause()
            return True
        else:
            logger.error("Analysis with ID %d not found."%aid)
            return False 
   
   
    def analysis_resume(self,aid):
        """
            Pause a given analysis
        """
        print "* Resumming analysis (%d)."%aid
        if aid in self.ANALYSIS_DICT:
            self.ANALYSIS_DICT[aid].resume()
            return True
        else:
            logger.error("Analysis with ID %d not found."%aid)
            return False
            
             
    def command_analysis(self,command,sock):
        """
            This command will stop all analysis if no arguments are given or
            the specified analysis referenced by ID number.
        """
        logger.debug("Got analysis command")
        # No command line arguments, stop everything
        if command.args is None or len(command.args) == 0:
            command.args = ANALYSIS_STATUS['running']
            
        rtn = True
        # Did this specifiy a specific analysis to stop?
        for aid in command.args:
            aid = int(aid)
            # What command should we run?
            if command.cmd == G.CTRL_CMD_STOP:
                rtn &= self.analysis_stop(aid)
            elif command.cmd == G.CTRL_CMD_PAUSE:
                rtn &= self.analysis_pause(aid)
            elif command.cmd == G.CTRL_CMD_UNPAUSE:
                rtn &= self.analysis_resume(aid)
            else:
                logger.error("Got unknown command: %s"%command.cmd)
            
        return rtn


    def command_start(self, command, sock):
        """
            Start all of our SUAs
        """
        logger.debug("Running start command. (%s)"%command)
        
        # Get our analysis class
        AnalysisClass = self._get_analysis(sock)
        
        if AnalysisClass is None:
            logger.error("Received an invalid analysis file.")
            return False
        
        logger.debug("Got analysis: %s"%AnalysisClass.__class__.__name__)
        
        # What kind of machine
        if command.machine_type is not None:
            machine_type = int(command.machine_type)
        else:
            machine_type = int(AnalysisClass.MACHINE_TYPE)
            
        # Add any relevant information to the command before starting the analysis
        if machine_type == G.MACHINE_TYPES.PHYSICAL:
            command.ftp_info['ip'] = self.ftp_ip_physical
        else:
            command.ftp_info['ip'] = self.ftp_ip_virtual
            
        # Update our services host
        command.services_host = self.services_host
            
        # Send the analysis to the scheduler
        self.ANALYSIS_SCHEDULER[machine_type].queue_analysis( (AnalysisClass, 
                                                               command) )
        
        return True


    def command_die(self, args, sock):
        """ Kill all our children, and then ourselves """
        self.command_abstract([G.CTRL_CMD_KILL], sock)
        self.RUNNING = False



    def command_list(self, args, sock):
        """
            Generic command to list statuses of the server
        """

        # See if the list exists and return results
        if len(args) > 1 and args[1] in self.LISTS:
            output = ""

            # Print out our available machines
            if args[1] == "machines":
                output = G.print_machines(self.machine_list)

            # Print out our running analyses
            if args[1] == "analysis":
                output = G.print_analyses(self.ANALYSIS_DICT)

            G.send_socket_data(sock, output)
            return True
        else:
            return False


    def command_pickle(self, command, sock):
        """
            Will pack our config lists and send them accross the socket
        """

        # See if the list exists and return results
        if len(command.args) > 0 and command.args[0] in self.LISTS:
            # Print out our available machines
            if command.args[0] == "machines":

                # Pack out list in a proto buf
                machine_buf = ProtoBuf.pack_machine_list(self.machine_list)

                # Send our serialized protocol buffer
                G.send_socket_data(sock, machine_buf)

                logger.debug("Sent list of machines.")
                return True

            # Print out our running analyses
            elif command.args[0] == "analysis":

                # Pack up our analysis list
                analysis_buf = ProtoBuf.pack_analysis_list(self.ANALYSIS_DICT)

                # Send it across the network
                G.send_socket_data(sock, analysis_buf)

                logger.debug("Sent analysis list.")
                return True
            
            else:
                return False

        else:
            G.send_socket_data(sock, "ERROR: No such list.\n"
                      "   Available lists are: %s\n" % self.LISTS)
            return False


    def proccess_input(self, clientsock):
        """"
            Continuously read and process commands from our socket
        """

        COMMANDS = {G.CTRL_CMD_START:self.command_start,
                    G.CTRL_CMD_STOP:self.command_analysis,
                    G.CTRL_CMD_PAUSE:self.command_analysis,
                    G.CTRL_CMD_UNPAUSE:self.command_analysis,
                    G.CTRL_CMD_LIST:self.command_list,
                    G.CTRL_CMD_PICKLE:self.command_pickle}

        try:
            # Loop forever
            while self.RUNNING:
                # Get the data
                try:
                    data = G.read_socket_data(clientsock)
                except socket.timeout:
#                     self._cleanup_pointers()
                    continue
                    
                if not data:
                    break

                # cleanup our pointers to give a 
#                 self._cleanup_pointers()

                # Split up our command
                cmd = LophiCommand.from_data(data) #.rstrip().split(" ")

                logger.debug("Got command: %s" % cmd)
                
                # See if it's valid command
                if cmd.cmd == "help":
                    G.send_socket_data(clientsock, "The available commands are: %s\n" %
                                     (COMMANDS.keys()))
                elif cmd.cmd not in COMMANDS.keys():
                    G.send_socket_data(clientsock,"Invalid Command: %s\n" % cmd.cmd)
                else:
                    rtn = COMMANDS[cmd.cmd](cmd, clientsock)
                    if rtn == True:
                        G.send_socket_data(clientsock, "Success.")
                    elif rtn == False:
                        G.send_socket_data(clientsock, "Failure.")
                        
                    
                
        except socket.error:
            logger.warning("Looks like our socket closed...")


    def run(self):
        """
            Setup our server and await commands
        """
        
        logger.info("Started LO-PHI controller. (PID: %d)"%os.getpid())

        # Our address to listen on
        LOPHI_ADDR = (G.LOPHI_HOST, self.PORT_NUM)

        # Open our socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Ignore the silly TIME_WAIT state
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Set a timeout so that we will keep cleaning up old pointers
#         sock.settimeout(60)
#         logger.debug("Set timeout on socket.")
        
        # Bind to our address/port
        BOUND = False
        while not BOUND:
            try:
                sock.bind(LOPHI_ADDR)
                BOUND = True
            except:
                print "* Cannot bind socket... (Retrying in %d seconds)" % G.LOPHI_BIND_RETRY
                time.sleep(G.LOPHI_BIND_RETRY)

        # Listen for a client (Only 1 at a time)
        sock.listen(2)
        
        self._sock = sock

        print "* Listening on %s:%s..." % (LOPHI_ADDR[0], LOPHI_ADDR[1])


        while self.RUNNING:

            try:
                clientsock, addr = sock.accept()
                clientsock.settimeout(60)
            except socket.timeout:
#                 self._cleanup_pointers()
                continue
                
            self.remote_address = addr
            print "* Got connection from %s:%s." % (addr[0], addr[1])
            self.proccess_input(clientsock)
            clientsock.close()

        # Close up shop
        sock.close()


        # Sleep for a few seconds, then kill everything
        print "* Shutting down server..."

        sys.exit(0)


