#!/usr/bin/env python
"""
    Example script for capturing network data

    (c) 2015 Massachusetts Institute of Technology
"""
#  Native
import sys
import optparse
import logging
logger = logging.getLogger(__name__)

# 3rd party
import dpkt

# LO-PHI
from lophi.sensors.network import NetworkSensor

def main(options):

    # Initialize our sensor
    net = NetworkSensor(options.interface)

    # Open a file to store our capture
    f = open("test.pcap", "a+")
    writer = dpkt.pcap.Writer(f)

    while True:
        (ts,packet) = net.read()
        
        # Start analyzing our packet
        eth_packet = dpkt.ethernet.Ethernet(packet)

        # Print packets to screen
        print repr(eth_packet)
        
        writer.writepkt(packet)
        
        f.flush()
        
    f.close()

if __name__ == "__main__":

    opts = optparse.OptionParser()
    
    opts.add_option("-i", "--interface", action='store', type="string",
                    help="Interface to sniff",
                    default=None, dest='interface')
    
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
        
    if options.interface is None:
        logger.error("You must define a networking interface.")
        opts.print_help()
        sys.exit(0)
        
    main(options)