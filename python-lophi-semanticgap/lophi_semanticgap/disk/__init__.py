"""
 This a script to interface with the disk introspection engine.
 It loads our python module for parsing the actual network data.
 It handles both local (VM) instances as well as physical hosts.

 Author: Chad Spensky (MIT Lincoln Laboratory)
"""
# Native
import multiprocessing
import os
import logging
logger = logging.getLogger(__name__)
import time
import subprocess

# LO-PHI

import lophi.globals as G

SOCKET_RETRY = 15 # Seconds

class DiskEngine(multiprocessing.Process):
    """
        A class for handling all of our disk polling.  It will open a network 
        connection, either to our VM server or a physical machine and wait
        for input.  One we see a read or write, we will write it to our queue
        for the aggregator to handle.
    """
    
    # LO-PHI Framework stuff
    PLUGIN_NAME = "disk_engine" # This name must not intersect with Volatility names


    def __init__(self, machine, 
                 command_queue=None, 
                 output_queue=None):
        """
            Initialize our analysis engine
        """

        # Init our multiprocess
        multiprocessing.Process.__init__(self)

        # Save our machine
        self.machine = machine

        # Our queue to talk to the control program
        self.output_queue = output_queue

        # Our command queue
        self.command_queue = command_queue
        
        self.working_disk_img = None
        
        # Keep track of if we are reporting output or not
        self.PAUSED = False
        
        
    def __del__(self):
        """ Cleanup our temp file """
        if self.working_disk_img is not None:
            os.unlink(self.working_disk_img)
        
        
    def _check_disk_scan(self):
        """ See if the disk scan file provided is valid """
        if self.machine.config.disk_scan is None:
            logger.error("No disk scan file given.")
            return False
        if not os.path.exists(self.machine.config.disk_scan):
            logger.error("Disk scan file '%s' does not exist." % self.machine.config.disk_scan)
            return False
            
        return True
    

    def report_output(self, output):
        """
            This is an abstract function to report output back out control 
            thread.  It also handles logging for this particular SUA
            
            Note: When you pause analysis, you will miss 1 disk access after
            the unpause due to how this is implemented
        """

        if self.output_queue is not None:
            self.output_queue.put(output, False)


    def parse_actions(self, timestamp, fs_operations):
        """
            Given a list of actions will parse them and report the results back
            to our aggregator through our queue.
        """
        # Anything new happen?
        if not fs_operations:
            return

        # aggregate actions since we do it sector by sector
        actions = []
        current_action = None
        last_sector = 0
        for fs_op in fs_operations:
        
            if not current_action:
                current_action = fs_op
                last_sector = current_action['sector']
                continue
        
            # check if this fs_op has the same inode and consecutive sector
            if ((fs_op['inode'] == current_action['inode']) and
                (fs_op['sector'] == last_sector + 1)):
            
                # aggregate the data and continue
                current_action['raw_data'] = current_action['raw_data'] + fs_op['raw_data']
                last_sector += 1
            
                #print "Aggregating inode %s, file %s, sector %d" % (str(fs_op['inode']), fs_op['filename'], fs_op['sector'])
            
            
            else:
                # otherwise, add the current_action to our list of actions and
                # start a new current_action based on fs_op
                actions.append(current_action)
                current_action = fs_op
                last_sector = current_action['sector']
        
        
        # make sure that the last current_action got added
        actions.append(current_action)

        # Setup our output dictionary to pass back to our aggreator
        output = {}
        
        # Meta Data
        output['MODULE'] = self.PLUGIN_NAME
        output['MACHINE'] = self.machine.config.name
        output['PROFILE'] = self.machine.config.volatility_profile        
        output['SENSOR'] = self.machine.disk.name
        
        # Append timestamp
        for a in actions:
            a["Timestamp"] = timestamp
            a["Content"] = ""
    
        # Header and data
        #  {'sector':sector, 'op':op, 'op_type':op_type, 'inode':mft_record_no, 'filename':filename, 'raw_data':raw_data, 'semantic_data':semantic_data}
        #output['HEADER'] = ['Timestamp','Operation','Filename','Content']
        output['HEADER'] = ['Timestamp','Operation','Filename','Sector','Semantic Data']
    
        out_data = []
    
        # Output each action
        for action in actions: 
            
            filename = ""
            original_path = ""
            # Debug info
            if action['filename'] is None:
                logger.debug("NOP")
            else:
                logger.debug("%s: %s" % (action['op_type'], action['filename']))

            semantic_data = None

            # Append to output    
            out_data.append([action['Timestamp'],
                             action['op_type'],
                             action['filename'],
                             action['sector'],
                             ""
                             ])
            
            if action['semantic_data'] is not None:
                for sd in action['semantic_data']:
                    if len(sd['changes']) > 0:
                        for change in sd['changes']:
                            
                            meta_old = str(sd['changes'][change]['old'])
                            meta_new = str(sd['changes'][change]['new'])
                            
                            if change == "atime" or change == "mtime" or change == "ctime":
                                meta_old = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                         time.localtime(sd['changes'][change]['old']))
                                meta_new = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                         time.localtime(sd['changes'][change]['new']))
                            
                            out_data.append([action['Timestamp'],
                                         "["+change.upper()+" MODIFIED]",
                                         sd['filename'],
                                         action['sector'],
                                         meta_old + " -> " + meta_new
                                         ])
                        

        output['DATA'] = out_data
    
#         for q in self.output_queues:
#             q.put(output)
            
#         for out in out_data:
#             if out[2] != "unknown":
#                 if isinstance(out[4],dict):
#                     print "%s %s"%(out[1],out[2])
#                 else:
#                     print "%s %s %s"%(out[1],out[2], out[4])
                    
        # report our output back and log it 
        self.report_output(output)



    def run(self):
        """
            Figure out which type of host we are examining and call the 
            appropriate function.
        """

        from lophi_semanticgap.disk.sata import SATAInterpreter
        from lophi_semanticgap.disk.sata_reconstructor import SATAReconstructor
        from lophi_semanticgap.disk.filesystem_reconstructor import SemanticEngineDisk

        logger.debug("DiskEngine Started.")

        # Scan in our starting point
        if self.machine.type == G.MACHINE_TYPES.PHYSICAL:
            if not self._check_disk_scan():
                logger.error("Analysis cannot continue without a valid scan file.")
                return
            
            disk_img = self.machine.config.disk_scan
        else:
            # Get our image name for the virtual HDD on this host
            image_name = self.machine.disk_get_filename()
            logger.debug("Scanning disk image (%s)..." % (image_name))

            if image_name is None:
                logger.error("No disk found for VM (%s)."%self.machine.config.name)
                return
            
            if image_name.endswith("qcow2"):
                logger.warning("Got qcow2 image, scanning the base image, ensure that you reset the machine!")
                disk_img = self.machine.config.disk_base
            else:
                disk_img = image_name
                
        # Setup our tmp file
        self.working_disk_img = os.path.join(G.DIR_ROOT,G.DIR_TMP,self.machine.config.name+"-disk.img.tmp")
        
        # Create a backup
        logger.debug("Copying %s to %s..."%(disk_img, self.working_disk_img))
        cmd = "cp --sparse=always %s %s" % (disk_img, self.working_disk_img)
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        os.chmod(self.working_disk_img, 0755)
        
        # Set up our semantic bridge
        logger.info("Parsing disk image %s into our semantic engine... (This may take a while)" % self.working_disk_img)
        semantic_engine = SemanticEngineDisk(self.working_disk_img)

        # SATA Interpreter
        sata = SATAInterpreter() 
        
        # SATA Interpreter
        sata_reconstructor = SATAReconstructor(sector_size=G.SENSOR_DISK.DEFAULT_SECTOR_SIZE)
        
        # Get data forever and report it back
        self.RUNNING  = True
        while self.RUNNING:
            
            # Accept commands
            try:
                cmd = self.command_queue.get(False).split(" ")
                logger.debug("Got cmd: %s" % cmd)
                if cmd[0] == G.CTRL_CMD_PAUSE:
                    logger.debug("Pausing analysis")
                    self.PAUSED = True
                    self.machine.disk._disconnect()
                if cmd[0] == G.CTRL_CMD_UNPAUSE:
                    logger.debug("Resuming Analysis")
                    self.PAUSED = False
                    self.machine.disk._connect()
                if cmd[0] == G.CTRL_CMD_KILL or cmd[0] == G.CTRL_CMD_STOP:
                    logger.debug("Got kill command")
                    self.RUNNING = False
                    self.machine.disk._disconnect()
                    break
            except:
                # Do nothing
                pass
            
            if self.PAUSED:
                time.sleep(1)
                continue
            
            # Get our packet
            try:
                data = self.machine.disk_get_packet()
                logger.debug("Got: %s"%data)
            except:
                G.print_traceback()
                logger.debug("Disk introspection socket closed.")
                break
            
            # Good data?
            if data is None:
                continue

            if self.machine.type == G.MACHINE_TYPES.PHYSICAL:
                lophi_packet = type('AnonClass', (object,), { "sata_header": None, "sata_data": None })                    
                (lophi_packet.sata_header, lophi_packet.sata_data) = sata.extract_sata_data(`data`)
                
                # deal with SATA NCQ reordering
                disk_sensor_pkts = sata_reconstructor.process_packet(lophi_packet)
            else:
                disk_sensor_pkts = [data]
                
            
            # Process all of our disk packets
            if disk_sensor_pkts:
                for dsp in disk_sensor_pkts:
                    # Skip empty packets
                    if not dsp:
                        continue
      
                    try:

                        fs_operations = semantic_engine.get_access(dsp.sector, 
                                                                   dsp.num_sectors, 
                                                                   dsp.disk_operation, 
                                                                   dsp.data)   
                        self.parse_actions(time.time(), fs_operations)                   
                               
                    except:
                        logging.exception("Encountered error while trying to bridge semantic gap for this disk access.")

            
#             logger.debug("got actions %s"%actions)
            # Handle our output
#             self.parse_actions(actions)

        logger.debug("Disk analysis exiting...")
        
        
        
class DcapEngine(multiprocessing.Process):
    """
        Very simple class used to capture SATA traffic and return it in a binary
        format suitable for storing it a PCAP
    """
    
    def __init__(self, machine, command_queue=None, output_queue=None):
        """
            Initialize our analysis engine
        """

        # Save our machine
        self.machine = machine

        # Our queue to talk to the control program
        self.output_queue = output_queue

        # Our command queue
        self.command_queue = command_queue
        
        # Init our multiprocess
        multiprocessing.Process.__init__(self)
        
    def run(self):
        """
            Capture packets from the wire and output them to our output queue
        """
        
        logger.debug("DcapEngine Started.")
        
        # Get data forever and report it back
        self.RUNNING = True
        self.PAUSED = False
        while self.RUNNING:
            
            try:
                cmd = self.command_queue.get(False).split(" ")
                logger.debug("Got cmd: %s" % cmd)
                if cmd[0] == G.CTRL_CMD_PAUSE:
                    logger.debug("Pausing analysis")
                    self.PAUSED = True

                if cmd[0] == G.CTRL_CMD_UNPAUSE:
                    logger.debug("Resuming Analysis")
                    self.PAUSED = False
                    
                if cmd[0] == G.CTRL_CMD_KILL or cmd[0] == G.CTRL_CMD_STOP:
                    logger.debug("Got kill command")
                    self.RUNNING = False
                    break
            except:
                # Do nothing
                pass
            
            if self.PAUSED:
                time.sleep(1)
                continue
            
            # Get a network packet and return it over our output queue
            capture = self.machine.disk_get_packet()
            
            if capture is None:
                continue
            
            logger.debug("Read packet from wire. (%s)"%capture)
                        
            
            
            self.output_queue.put(capture)
            logger.debug("added packet to queue")
            
        logger.debug("Disk Engine stopped.")
        self.stop()
        
    def stop(self):
        """ Kill our process nicely """
        logger.debug("Killing disk capture process...")
        self.output_queue.close()
        self.terminate()

        
