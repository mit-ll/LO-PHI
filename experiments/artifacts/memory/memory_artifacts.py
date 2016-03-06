#!/usr/bin/env python
"""
   This is our script to run our experiment to show minimal artifacts with
    our SATA sensor using IOZone
    
    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import os
import sys
import logging
logger = logging.getLogger(__name__)
import argparse
import multiprocessing
import threading
import time

# LO-PHI
import lophi.globals as G
import lophi.network as NET
import lophi.configs.helper as CONF
from lophi.machine.virtual import VirtualMachine
from lophi.analysis.remote import RemoteAnalysis
from lophi.sensors.control.physical import ControlSensorPhysical
from lophi.sensors.control.virtual import ControlSensorVirtual
from lophi.capture import CaptureWriter
from lophi.analysis import DiskCaptureEngine


class MemoryThread(threading.Thread):
    """
            Read the first 1GB of memory forever.  Used for stress testing.
    """
        
    def __init__(self,machine):
        self.machine = machine
        self._stop = threading.Event()
        self.total_bytes = 0
        self.total_time = 0
        
        threading.Thread.__init__(self)
        
    def run(self):
        print "* Reading memory until stopped..."
        start = time.time()
        
        while not self._stop.isSet():
            self.machine.memory_read(0,1000000000)
            self.total_bytes += 1000000000
            print " * Read %dGB"%(self.total_bytes/1000000000)
        
        self.total_time = time.time() - start
        
        print "* Done reading memory."
                
        
    def join(self, timeout=None):
        self._stop.set()
        super(MemoryThread, self).join(timeout)
        
        return (self.total_time, self.total_bytes)
        
    

def run_analysis(options):

    # Get our FTP IP
    try:
        ftp_ip = NET.get_ip_address(options.ftp_interface)
    except:
        logger.error("Could not find ip for the given interface. (%s)"%
                     options.ftp_interface)
            
    # Add a sensors to physical machines if needed
    if options.machine_type == G.MACHINE_TYPES.PHYSICAL:
        has_memory = has_disk = False
        
        if options.machine_config is None:
            logger.error("No machine config file given.")
            return
        
        # This isn't the class we use in practice, but fake it here for simplicity
        machines = CONF.import_from_config(options.machine_config, "machine")
    
        if options.machine not in machines:
            logger.error("%s is not a valid machine from the config file."%options.machine)
            logger.error("Valid targets are: %s"%machines.keys())
            return

        # Get our machine object
        machine = machines[options.machine]
            
        # Ensure that a sensor config is defined
        if options.sensor_config is None:
            logger.error("A sensor config file must be defined for physical analysis")
            return
        # Get the list of sensors
        sensors = CONF.import_from_config(options.sensor_config, "sensor")
        
        # Add sensors to our machine
        print "* Trying to find physical sensors for %s..."%options.machine
        added_sensors = machine.add_sensors(sensors)
        
    else:
        machine = VirtualMachine(options.machine,
                                 vm_type=options.machine_type,
                                 volatility_profile=options.profile)
        
        
    
    ftp_info = {'user':G.FTP_USER,
                 'pass':G.FTP_PASSWORD,
                 'ip':ftp_ip,
                 'port':G.FTP_PORT,
                 'dir':None
                 }
    
    print "* Machine is: %s"%machine.power_status()
    
    ra = RemoteAnalysis(options.profile, machine.control, ftp_info)
        

        
    parameters = {
#                   1:'INTmark (write)',
#                   2:'INTmark (Read)',
                  3:'INTmem',
#                   4:'FLOATmark (write)',
#                   5:'FLOATmark (Read)',
                  6:'FLOATmem',
#                   7:'MMXmark (write)',
#                   8:'MMXmark (Read)',
                  9:'MMXmem',
#                   10:'SSEmark (write)',
#                   11:'SSEmark (Read)',
                  12:'SSEmem'
                  }
    # Create a run for all of our parameters (Only *mem will run in batches)
    for b_param in parameters:
        # Should we be reading memory?
        if options.enable_sensor:
            memory_thread = MemoryThread(machine)
            memory_thread.daemon = True
            memory_thread.start()
        
        param_name = parameters[b_param]
        
        print "* Running %s test, %d times..."%(param_name, 
                                                options.run_count)
        
        response = ra.run_analysis("ramspeed-win32.exe -b %d -l %d"%(
                                                        b_param,
                                                        options.run_count),
                                    "artifacts-memory",
                                    init_commands=[],
                                    bind_ip=ftp_ip)
        
        # Now store our results
        results_file = os.path.join(options.output_dir,
                                    "trial_b%d_l%d.txt"%(b_param,
                                                         options.run_count))
        sensor_file = os.path.join(options.output_dir,
                                    "trial_b%d_l%d_sensor.txt"%(b_param,
                                                         options.run_count))
        print "* Storing results (%d bytes) in %s."%(len(response),results_file)
        f = open(results_file, "w+")
        f.write(response)
        f.close()
    
        if options.enable_sensor:
            (time_elapsed, bytes_read) = memory_thread.join()
            f = open(sensor_file, "w+")
            f.write(str(time_elapsed)+"\t"+str(bytes_read))
            f.close()
        


if __name__ == "__main__":
    
     # Import our command line parser
    args = argparse.ArgumentParser()
 
#     args.add_argument("-t", "--target", action="store", type=str, default=None,
#                       help="Target for control sensor.  (E.g. 172.20.1.20 or VMName)")
    
    # Add any options we want here
    machine_config = os.path.join(G.DIR_ROOT, G.DIR_CONFIG, G.CONFIG_MACHINES)
    args.add_argument("-c", "--config", action="store", type=str,
        dest="machine_config", default=machine_config,
        help="Config file containing machine descriptions.")
    
    # Sensors
    sensor_config = os.path.join(G.DIR_ROOT, G.DIR_CONFIG, G.CONFIG_SENSORS)
    args.add_argument("-s", "--sensor_config", action="store", type=str,
        dest="sensor_config", default=sensor_config,
        help="Config file containing sensor descriptions.")
    
    args.add_argument("-m", "--machine", action="store", type=str,
        dest="machine", default=None,
        help="Machine to perform analysis on.")
    
    args.add_argument("-T", "--machine_type", action="store", type=int,  
                      default=None,
                      help="Type of machine [%d - Physical, %d - KVM]"%(
                                                                       G.MACHINE_TYPES.PHYSICAL,
                                                                       G.MACHINE_TYPES.KVM))
    args.add_argument("-p", "--profile", action="store", type=str,  
                      default=None,
                      help="System profile. (E.g. WinXPSP3x86)")
    
    args.add_argument("-i", "--ftp_interface", action="store", type=str,  
                      default=None,
                      help="FTP Interface (E.g. eth3, lophi-virt)")
    
    args.add_argument("-o", "--output_dir", action="store", type=str,  
                      default=None,
                      help="Output Directory for test results.")
    
    args.add_argument("-r", "--run_count", action="store", type=int,  
                      default=10,
                      help="Number of times to run analysis.")
    
    args.add_argument("-S","--enable_sensor", action="store_true", 
                      default=False,
                      help="Enable the sensor that should produce artifacts")
    
    # Debug
    args.add_argument("-d", "--debug", action="store_true", help="Enable DEBUG")
     
    # Get arguments
    options = args.parse_args()
    
    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
        
    # Ensure we have our target info
    if options.machine is None:
        logger.error("You must provide a target.")
        args.print_usage()
        sys.exit(0)
    if options.machine_type is None:
        logger.error("You must provide a machine type.")
        args.print_usage()
        sys.exit(0)
    if options.profile is None:
        logger.error("You must provide a machine profile.")
        args.print_usage()
        sys.exit(0)
    
    # We need to know which interface the machien is on
    if options.ftp_interface is None:
        logger.error("You must provide an ftp interface.")
        args.print_usage()
        sys.exit(0)
        
    # Make sure we have a place for output
    if options.output_dir is None:
        logger.error("You must provide an output directory.")
        args.print_usage()
        sys.exit(0)
    elif os.path.exists(options.output_dir):
        logger.error("Directory '%s' already exists."%options.output_dir)
        sys.exit(0)
    else:
        try:
            os.makedirs(options.output_dir, 0755)
        except:
            logger.error("Could not make directory '%s'"%options.output_dir)
            sys.exit(0)
        
        
        
    run_analysis(options)