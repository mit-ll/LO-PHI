"""
    This script will instruct a physical machine or VM
    to run a binary for a specified amount of time

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import logging
logger = logging.getLogger(__name__)

import optparse
import sys
import os
import socket
import time
import multiprocessing

# LO-PHI

sys.path.append(os.path.join(os.getcwd(), "../"))
sys.path.append(os.path.join(os.getcwd(), "../../"))
os.chdir("../../")
import lophi.globals as G

from lophi.sensors.memory import MemorySensor
from lophi.sensors.disk import DiskSensor
from lophi.sensors.cpu import CPUSensor
from lophi.sensors.control import ControlSensor

from lophi.actuation.keypressgenerator import KeypressGeneratorPhysical,KeypressGeneratorVirtual

from lophi.analysis import MemoryAnalysisEngine
from lophi.analysis import DiskAnalysisEngine
import lophi.configs.helper as CONF



class DiskAnalysisProcess(multiprocessing.Process):
    
    def __init__(self, machine):
        multiprocessing.Process.__init__(self)
        
        self.machine = machine
        
        
    def start(self):
        if self.machine.disk is None:
            logger.error("Machine does not have disk sensor!")
            sys.exit(0)
        
        disk_sensor = self.machine.disk
        
        # connect to disk sensor
        disk_sensor._connect()

        if self.machine.type == G.MACHINE_TYPES.PHYSICAL:
            print "Printing registers..."
            disk_sensor.print_all_registers()
            print "Modifying Registers..."
            disk_sensor.sata_enable_all()
            disk_sensor.set_udp_delay(200)
            disk_sensor.print_all_registers()
    
        print "Reading packets..."
        while 1:

            # Get our packet
            packet = disk_sensor.get_disk_packet()

            # TODO: log the packet
            
        
    

def main(options):
    """
        Main function
    """
    
    if options.machine_config is None:
        logger.error("No config file given.")
        return
        
    if options.command_file is None:
        logger.error("No script file provided.")
        return

    # This isn't the class we use in practice, but fake it here for simplicity
    # Get list of machine objects
    machines = CONF.import_from_config(options.machine_config, "machine")
    
    
    if options.machine not in machines:
        logger.error("%s is not a valid machine from the config file."%options.machine)
        logger.error("Valid targets are: %s"%machines.keys())
        return
    
    machine = machines[options.machine]
    
    # Add a sensors to physical machines if needed
    if machine.type == G.MACHINE_TYPES.PHYSICAL:
        has_memory = has_disk = False
        
        # Ensure that a sensor config is defined
        if options.sensor_config is None:
            logger.error("A sensor config file must be defined for physical analysis")
            return
        # Get the list of sensors
        sensors = CONF.import_from_config(options.sensor_config, "sensor")
        
        # Add sensors to our machine
        print "Trying to find physical sensors for %s..."%options.machine
        added_sensors = machine.add_sensors(sensors)

        

    # Check that we can do both memory and disk analysis
    if not machine.memory:
        logger.error("No memory sensor available for analysis!  Quitting.")
        return

    if not machine.disk:
        logger.error("No disk sensor available for analysis!  Quitting.")
        return

    if not machine.control:
        logger.error("No control sensor available for analysis!  Quitting.")
        return

    # load the command script
    if not os.path.exists(options.command_file):
        logger.error("File (%s) does not exist!" % options.command_file)
        sys.exit(0)

    # prepare the command script parser
    parser = None
    if machine.type == G.MACHINE_TYPES.PHYSICAL:
        parser = KeypressGeneratorPhysical()
    else:
        parser = KeypressGeneratorVirtual()

    # open file                                                         
    f = open(options.command_file, 'r')
    script_text = f.read()
    f.close()

    script = parser.text_to_script(script_text)

    # Start the trials
    for trial_num in range(options.trials):

        print "Running trial %d" % trial_num
 
        # Prep the machine -- reset it
 
        if machine.type != G.MACHINE_TYPES.PHYSICAL:
            machine.machine_reset()
        else:
            machine.machine_reset(options.pxe_server)

        machine.power_off()
        # Wait for machine to shutdown
        time.sleep(15)
 
        # Wait until machine has an ip address
        logger.info("Waiting to get IP address of machine from PXE Server.")
        start_time = time.time()
        timeout = 360
        
        while True:   
            #machine.ip_addr = get_ip(options.pxe_server, machine.get_mac_addr())
            if (time.time() - start_time) > timeout:
                logger.error("Could not get ip address for test machine from PXE Server for %d s" % timeout)
                break
            ip = machine.get_ip_addr(options.pxe_server)
            if ip:
                logger.info("Machine has IP address %s" % ip)
                break
 
        # wait until machine is up
        logger.info("Waiting for machine to be up on the network.")
        start_time = time.time()
        timeout = 360
        while True:
            if (time.time() - start_time) > timeout:
                logger.error("Timed out while waiting for machine to come back up (e.g. waiting for system to boot)")
                break
                    
            if machine.get_net_status():
                break
            
        logger.info("Machine is back up.  Commencing analysis.")

        if machine.type != G.MACHINE_TYPES.PHYSICAL:
            logger.info("Pausing Virtual Machine!")
            machine.machine_pause()
        else:
            # pass
            logger.info("Pausing Physical Machine Not Implemented Yet!")

        # Take memory snapshot #1

        logger.info("Taking start memory dump")
        #memory_dump(machine, os.path.join(options.output_dir, "mem_dump_start" + str(trial_num)))

        # TODO: Spawn data consumers for disk and memory?

        logger.info("TODO: Starting disk analysis")
        
        
        # Resume machine
        if machine.type != G.MACHINE_TYPES.PHYSICAL:
            logger.info("Resuming Virtual Machine!")
            machine.machine_resume()
        else:
            # pass
            logger.info("Resuming Physical Machine Not Implemented Yet!")


        # Run command script and wait runtime seconds
        logger.info("Running %s script for %d seconds." % (options.command_file, options.runtime))

        machine.keypress_send(script)
        time.sleep(options.runtime)


        # pause machine if VM
        if machine.type != G.MACHINE_TYPES.PHYSICAL:
            logger.info("Pausing Virtual Machine!")
            machine.machine_pause()
        else:
            # pass
            logger.info("Pausing Physical Machine Not Implemented Yet!")
   
        logger.info("TODO: Stopping disk analysis")
        #disk_analysis.stop()

    
        # Take memory snapshot #2
        logger.info("Taking end memory dump")
        #memory_dump(machine, os.path.join(options.output_dir, "mem_dump_end" + str(trial_num)))


        # Resume machine
        if machine.type != G.MACHINE_TYPES.PHYSICAL:
            logger.info("Resuming Virtual Machine!")
            machine.machine_resume()
        else:
            # pass
            logger.info("Resuming Physical Machine Not Implemented Yet!")

        print "Completed trial %d" % trial_num


    print "Completed all trials."



def reset_vm(machine, parser):
    # reboot the machine
    machine.power_shutdown()
    time.sleep(30)
    machine.power_on()

    # wait about 5 seconds?
    time.sleep(5)

    # press special key for boot menu
    machine.keypress_send([parser.parse_special("F12")])
    machine.keypress_send([parser.parse_special("F12")])
    machine.keypress_send([parser.parse_special("F12")])

    # pick PXE boot
    machine.keypress_send([parser.parse_text("2")])
    
    # wait for PXE boot
    time.sleep(10)

    # pick the appropriate clonezilla batch job
    machine.keypress_send([parser.parse_special("RETURN")])


def reset_phys(machine, parser, options):
#     machine.power_on()
# 
#     # Machine will be set to automatically pxe boot and reset itself
#     # add machine's mac address to acl server
#     add_mac(options.pxe_server, machine.get_mac_addr())
# 
#     time.sleep(120)
# 
#     # delete machine's mac address from acl server so that machine will
#     # timeout its pxe boot and boot from its hard drive
#     del_mac(options.pxe_server, machine.get_mac_addr())
    pass


# def add_mac(pxe_server, mac_addr):
#     msg = G.PXE_ADD_ACL + mac_addr
#     send(msg, pxe_server, G.PXEBOOT_PORT)
#     
# 
# def del_mac(pxe_server, mac_addr):
#     msg = G.PXE_DEL_ACL + mac_addr
#     send(msg, pxe_server, G.PXEBOOT_PORT)
# 
# def get_ip(pxe_server, mac_addr):
#     msg = G.PXE_GET_IP + mac_addr
#     #resp = send(msg, pxe_server, G.PXEBOOT_PORT)[0]
#     resp = send(msg, pxe_server, 4011)[0]
#     if resp == G.PXE_NO_IP_RESP:
#         return None
#     else:
#         return resp
# 
# def send(msg, ip, port):
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     logger.info("Sending to PXE Server: %s" % msg)
#     sock.sendto(msg, (ip, port))
# 
#     # get response
#     resp = sock.recvfrom(512)
#     logger.info("Got response: %s" % resp[0])
#     return resp

def reset(machine, parser, options):
    """
       Resets machine to a saved state.  For testing purposes only.
       Will eventually be ported to machine.machine_reset()
    """
    if machine.type != G.MACHINE_TYPES.PHYSICAL:
        reset_vm(machine, parser)
    else:
        reset_phys(machine, parser, options)


def memory_dump(machine, output_filename):
    """
       Records memory snapshot
    """
    # Create output file

    try:
        os.makedirs(os.path.dirname(output_filename))
    except:
        pass

    try:
        output_file = open(output_filename, "w+")
    except:
        print "ERROR: Could not open output file."
        sys.exit(0)


    start_addr = 0  # TODO bug in KVM cannot read first 8 bytes
    if machine.type != G.MACHINE_TYPES.PHYSICAL:
        start_addr = 8
    MEM_SIZE = machine.memory.get_memsize()
    READ_SIZE = (32 * 1024) # 32K

    if MEM_SIZE < READ_SIZE:
        READ_SIZE = MEM_SIZE

    # Read memory
    print "Reading memory from %d to %d" % (start_addr, MEM_SIZE)
    
    # Get memory from remote system                                     
    read_addr = start_addr
    for addr in range(start_addr, start_addr+(MEM_SIZE / READ_SIZE)):

        logger.debug("Reading %d chunks of size %d bytes from 0x%016x"%(READ_SIZE,MEM_SIZE,addr))

        # Read memory                                                   
        data = machine.memory_read(read_addr, READ_SIZE)
        # Set point to the next chunk                                   
        read_addr += READ_SIZE

        # Write to file
        output_file.write(data)

    # Close output file                                                     
    output_file.close()

    print "Memory dump (%d bytes) written to %s." % (MEM_SIZE*READ_SIZE,output_filename)        

    

if __name__ == "__main__":

    # Import our command line parser
    opts = optparse.OptionParser()

    # Get our machine types
    machine_types = {}
    for x in G.MACHINE_TYPES.__dict__:  # @UndefinedVariable
        if x != "ASCII" and not x.startswith("_"):
            machine_types[x] = G.MACHINE_TYPES.__dict__[x] # @UndefinedVariable

    # Machine configs
    opts.add_option("-c", "--config", action="store", type="string",
        dest="machine_config", default=None,
        help="Config file containing machine descriptions.")
    
    # Sensors
    opts.add_option("-s", "--sensor_config", action="store", type="string",
        dest="sensor_config", default=None,
        help="Config file containing sensor descriptions.")

    # Comand line options
    opts.add_option("-m", "--machine", action="store", type="string",
        dest="machine", default=None,
        help="Machine to perform analysis on.")
    
    # Command file to run
    opts.add_option("-f", "--command-file", action="store", type="string",
        dest="command_file", default=None,
        help="Command file containing keyboard commands to send to the machine.")

    # Time to run in seconds
    opts.add_option("-r", "--runtime", action="store", type="int",
        dest="runtime", default=300,
        help="Total time to run the binary")

    # Number of trials to run
    opts.add_option("-t", "--trials", action="store", type="int",
        dest="trials", default=300,
        help="Total number of trials")

    # output directory for memory sensor
    opts.add_option("-o", "--out-dir", action='store', type="string",
                    help="Output directory to save memory dump to. (Default: mem_dumps)", default="mem_dumps", dest='output_dir')

    opts.add_option("-d", "--debug", action="store_true",
        dest="debug", default=False,
        help="Enable DEBUG")
    
    # PXE server
    opts.add_option("-p", "--pxe_server", action='store', type="string",
                    help="IP of PXE server. E.g. 127.0.0.1", dest='pxe_server')


    # Get arguments
    (options, positionals) = opts.parse_args(None)
   
    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    
        
    # start program
    main(options)
