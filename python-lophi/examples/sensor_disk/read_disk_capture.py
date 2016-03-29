#!/usr/bin/python
"""
    Example script for reading back the data captured from a disk stream

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import os
import sys
import argparse
import time
import multiprocessing
import subprocess
import logging
logger = logging.getLogger(__name__)


# LOPHI
import lophi.globals as G
from lophi.data import DiskSensorPacket
from lophi.capture import CaptureReader
from lophi.data import SATAFrame


def read_disk(options):

    # Setup our log files 
    dcap_filename = options.dcap_file

    # read from the cap file in real time
    reader = CaptureReader(options.dcap_file)

    # Tailing or terminating?
    reader_iter = reader
    if options.tail_enable:
        reader_iter = reader.tail()

    # Loop over all of the dcap contents
    for (timestamp, data) in reader_iter:

        print timestamp
        if options.sensor_type == G.MACHINE_TYPES.PHYSICAL:
            sata_frame = SATAFrame(data)
            print sata_frame
        else:
            disk_sensor_pkt = [DiskSensorPacket(data)]
            print disk_sensor_pkt


if __name__ == "__main__":
    # Get our machine types
    machine_types = {}
    for x in G.MACHINE_TYPES.__dict__:
        if x != "ASCII" and not x.startswith("_"):
            machine_types[x] = G.MACHINE_TYPES.__dict__[x]
            
    # Import our command line parser
    parser = argparse.ArgumentParser()

    # Input dcap
    parser.add_argument(action="store", dest="dcap_file",
                        default=None,
                        help="Filename of a disk capture file. (e.g. lophi_disk_capture.dcap")

    # Tail or offline analysis?
    parser.add_argument("-t", "--tail", action="store_true", dest="tail_enable",
                        default=False,
                        help="Continuing tailing file. (Useful for live analysis)")

    # Capture type
    parser.add_argument("-T", "--type", action="store", type=int,
        dest="sensor_type", default=0,
        help="Type of sensor. %s"%machine_types)
    
    # Debug
    parser.add_argument("-d", "--debug", action="store_true", help="Enable DEBUG")
     
    # Get arguments
    options = parser.parse_args()
    
    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
        
    # Make sure a dcap was given
    if options.dcap_file is None:
        logger.error("Please specify a disk capture file.")
        parser.print_help()
        sys.exit(-1)
    elif not os.path.exists(options.dcap_file):
        logger.error("Disk capture file does not exist. (%s)"%options.dcap_file)
        parser.print_help()
        sys.exit(-1)

    read_disk(options)



