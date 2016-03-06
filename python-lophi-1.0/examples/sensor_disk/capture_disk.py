#!/usr/bin/python
"""
    Example script for capturing disk data from sensors

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import os
import sys
import optparse
import time
import datetime
import multiprocessing
import logging
logger = logging.getLogger(__name__)

# LOPHI
import lophi.globals as G
from lophi.sensors.disk.physical import DiskSensorPhysical
from lophi.sensors.disk.virtual import DiskSensorVirtual
from lophi.capture import CaptureWriter

# Defaults
default_dest_ip = "172.20.1.2"


def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.3f %s" % (num, x)
        num /= 1024.0

def main(options):
    """
        This script will connect to the LO-PHI Disk Sensor and log all of the 
        activity to both a dcap file with RAW data capture
    """
    
    # Should we automatically set a output dir?
    OUTPUT_DIR = options.output_dir
    if OUTPUT_DIR is None:
        OUTPUT_DIR = "lophi_data_"+datetime.datetime.now().strftime("%m%d")
        
    # Make sure we can create the output directory
    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR)
        except:
            logger.error("Could not create output directory. (%s)"%OUTPUT_DIR)
            return
    
    # Auto-generate our dcap filename
    log_dcap_filename = os.path.join(OUTPUT_DIR, "lophi_disk_"+datetime.datetime.now().strftime("%m-%d-%H:%M")+".dcap")

    print "* Initializing SATA sensor..."                
    
    # Initialize our disk sensor    
    if options.sensor_type == G.MACHINE_TYPES.PHYSICAL:
        disk_sensor = DiskSensorPhysical(G.SENSOR_DISK.DEFAULT_IP,
                                     bind_ip=default_dest_ip,
                                     name="SATA_Sensor")
        
        if not disk_sensor.is_up():
            logger.error("Disk sensor appears to be down.")
            return
    else:
        disk_sensor = DiskSensorVirtual(options.target)
        
    print "* Logging data to: %s" % log_dcap_filename

    print "* Setting up DCAP logger..."
    # Setup our dcap logger
    # We use a queue so that we don't hold up the socket.
    log_dcap_queue = multiprocessing.Queue()
    log_dcap_writer = CaptureWriter(log_dcap_filename,
                                    log_dcap_queue)
    log_dcap_writer.start()
        
    print "* Connecting to our sensor..."
    
    # Get data forever and report it back
    disk_sensor._connect()

    if options.sensor_type == G.MACHINE_TYPES.PHYSICAL:
        print "* Enabling SATA extraction..."
        disk_sensor.sata_enable_all()
        
        print "* Reading SATA Frame packets..."
        
    else:
        print "* Reading Disk Sensor Packets..."
    
    UPDATE_INTERVAL = 5 # Seconds
    last_print_time = 0
    while 1:
        try:
            # Get our packet
            # Returns a SATAFrame for physical and DiskSensorPacket for virtual.
            packet = disk_sensor.get_disk_packet()    

            # Log to 
            if log_dcap_queue is not None:
                log_dcap_queue.put( packet )     
                
            # Should we print something to screen?
            now = time.time()
            if now - last_print_time > UPDATE_INTERVAL:
                size = sizeof_fmt(os.path.getsize(log_dcap_filename))
                print "* Captured %s."%size
                last_print_time = now
                                
        except:
            logger.error("Problem getting disk packet.")
            G.print_traceback()
            break
            
    if log_dcap_queue is not None:
        log_dcap_writer.stop()
        
    if options.sensor_type == G.MACHINE_TYPES.PHYSICAL:
        disk_sensor.sata_disable()
    
    return

if __name__ == "__main__":
    # Get our machine types
    machine_types = {}
    for x in G.MACHINE_TYPES.__dict__:
        if x != "ASCII" and not x.startswith("_"):
            machine_types[x] = G.MACHINE_TYPES.__dict__[x]
            
    # Import our command line parser
    opts = optparse.OptionParser()
    
    # Comand line options
    opts.add_option("-t", "--target", action="store", type="string",
        dest="target", default=G.SENSOR_DISK.DEFAULT_IP,
        help="IP address of physical card or name of VM to attach to.")
    
    opts.add_option("-T", "--type", action="store", type="int",
        dest="sensor_type", default=0,
        help="Type of sensor. %s"%machine_types)
    
    # Record/Replay
    opts.add_option("-o", "--output_directory", action="store", type="string",
        dest="output_dir", default='.',
        help="Directory to output log files to.")
    
    # Debug
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
    
    main(options)