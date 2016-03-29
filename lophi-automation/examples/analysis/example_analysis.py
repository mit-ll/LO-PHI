"""
    This file shows how to perform both disk and memory analysis.
    
    This just prints ugly output to the command line.
    In a real use case, a data consumer would be used.
    
    !! IMPORTANT !!
    
    Be very careful when defining command line parameters as Volatiilty will 
    inherit them!
    
    !! IMPORTANT !!

    (c) 2015 Massachusetts Institute of Technology
"""
# Navtive
import logging
logger = logging.getLogger(__name__)

import optparse
import sys
import os
import multiprocessing
import time

# LO-PHI
import lophi.globals as G

import lophi.configs.helper as HELPER
from lophi.sensors.memory import MemorySensor
from lophi.sensors.disk import DiskSensor
from lophi.machine.virtual import VirtualMachine
from lophi.analysis import MemoryAnalysisEngine
from lophi.analysis import DiskAnalysisEngine,DiskCaptureEngine, LoPhiAnalysisEngine

from lophi.capture import CaptureWriter,CaptureReader

import lophi.configs.helper as CONF

analysis_dir = os.path.join(G.DIR_ROOT,G.DIR_ANALYSIS_SCRIPTS)
analysis_scripts = HELPER.import_analysis_scripts(analysis_dir)

def main(options):
    """
        Implement your function here
    """
 
    # Keep track of the type of analysis that is possible (for physical)
    has_memory = has_disk = True
    
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
        print "Trying to find physical sensors for %s..."%options.machine
        added_sensors = machine.add_sensors(sensors)
        
        # See which sensors were added
        for sensor in added_sensors:
            print "* Added %s to %s"%(sensor.id,machine.config.name)
            if issubclass(sensor.__class__,MemorySensor):
                has_memory = True
            if issubclass(sensor.__class__,DiskSensor):
                has_disk = True
    else:
        machine = VirtualMachine(options.machine,
                                 vm_type=options.machine_type,
                                 volatility_profile=options.volatility_profile)
        
    if options.analysis is not None:
        analysis = analysis_scripts[options.analysis]
        
        lae = LoPhiAnalysisEngine()
        lae.start(analysis[0],machine=machine)
        
        print "Running Analysis (%s)..."%options.analysis
        while True:
            print "* The following commands are available"
            print "   p - Pause, r - Resume, s - Stop"
            command = raw_input('cmd: ')
            
            if command == "p":
                lae.pause()
                print "Analysis PAUSED."
                
            elif command == "r":    
                lae.resume()    
                print "Analysis RESUMED."
                            
            elif command == "s":
                lae.stop()
                print "Analysis STOPPED."
                sys.exit(0)
            else:
                print "Unrecognized command (%s)."%command
        
        
        
     
    
    if False and has_memory:
        print "Starting memory analysis"
        # Create a queue and start our analysis
        output_queue = multiprocessing.Queue()
        mem_analysis = MemoryAnalysisEngine(machine,
                                            output_queue,
                                            plugins=['pslist'])
        mem_cap = CaptureWriter("memory.cap",output_queue)
#         mem_cap.start()
        mem_analysis.start()
        
        for i in range(10):
            print output_queue.get()
        
#         mem_cap.stop()
        mem_analysis.stop()

        
    if has_disk:
        print "Starting disk analysis"
        # create a queue and start analysis
        output_queue = multiprocessing.Queue()
        disk_analysis = DiskAnalysisEngine(machine,
                                           output_queue)
        disk_cap = CaptureWriter("disk.cap",output_queue)
#         disk_cap.start()
        
        disk_analysis.start()
        
        for i in range(100):
            print output_queue.get()
            
#         disk_cap.stop()
        disk_analysis.stop()
   

if __name__ == "__main__":

    # Import our command line parser
    opts = optparse.OptionParser()

    # Get our machine types
    machine_types = {}
    for x in G.MACHINE_TYPES.__dict__:  # @UndefinedVariable
        if x != "ASCII" and not x.startswith("_"):
            machine_types[x] = G.MACHINE_TYPES.__dict__[x] # @UndefinedVariable

    # Add any options we want here
    opts.add_option("--profile", action="store", type="string",
        dest="volatility_profile", default=None,
        help="Volatility profile of the machine. (E.g. WinXPSP3x86)")
    
    # Add any options we want here
    machine_config = os.path.join(G.DIR_ROOT, G.DIR_CONFIG, G.CONFIG_MACHINES)
    opts.add_option("-c", "--config", action="store", type="string",
        dest="machine_config", default=machine_config,
        help="Config file containing machine descriptions.")
    
    # Sensors
    sensor_config = os.path.join(G.DIR_ROOT, G.DIR_CONFIG, G.CONFIG_SENSORS)
    opts.add_option("-s", "--sensor_config", action="store", type="string",
        dest="sensor_config", default=sensor_config,
        help="Config file containing sensor descriptions.")

    # Analysis option
    opts.add_option("-a", "--analysis", action="store", type="string",
        dest="analysis", default=None,
        help="Analysis script to run. Options: %s"%
            analysis_scripts.keys())
    

    # Comand line options
    opts.add_option("-m", "--machine", action="store", type="string",
        dest="machine", default=None,
        help="Machine to perform analysis on.")
    
    opts.add_option("-T", "--type", action="store", type="int",
        dest="machine_type", default=None,
        help="Type of machine. %s"%machine_types)
    

    opts.add_option("-d", "--debug", action="store_true",
        dest="debug", default=False,
        help="Enable DEBUG")
    
    # Get arguments
    (options, positionals) = opts.parse_args(None)
   
    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()

    
    # What machine type are we initializing?
    if options.machine_type is None:
        logger.error("Please specify a machine type.")
        opts.print_help()
        sys.exit(0)
        
    # Volatility profile
    if options.volatility_profile is None:
        logger.error("No Volatility profile provided.")
        opts.print_help()
        sys.exit(0)
        
    # Machine name
    if options.machine is None:
        logger.error("No machine name provided.")
        opts.print_help()
        sys.exit(0)
    

    # start program
    main(options)
