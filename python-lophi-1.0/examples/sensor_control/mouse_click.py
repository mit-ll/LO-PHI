#!/usr/bin/env python
"""
    This is an example of using our RFB library to interact with VNC servers
    
    (c) 2015 Massachusetts Institute of Technology
"""

import logging
import os
import sys
import optparse
logger = logging.getLogger(__name__)
import lophi.actuation.rfb as rfb


def main(options,positionals):
    """
        Command line interface to our VNC Client
    """
    
    x = int(positionals[0])
    y = int(positionals[1])
    
    
    vnc_client = rfb.RFBClient()
    vnc_client.mouseMove(x ,y)
    vnc_client.mouseClick(options.button,double_click=options.double_click)

if __name__ == "__main__":

    # Import our command line parser
    opts = optparse.OptionParser(usage="Usage: %prog [options] <X coord> <y coord>")

    # Add any options we want here
    opts.add_option("-i", "--server_ip", action="store", type="string",
        dest="server_ip", default="localhost",
        help="IP Address of VNC server. (Default: localhost)")
    
    opts.add_option("-p", "--vnc_port", action="store", type="int",
        dest="vnc_port", default=0,
        help="VNC port of the system we are connecting to. (Default: 5900)")

    opts.add_option("-C", "--double_click", action="store_true",
        dest="double_click", default=False,
        help="Double click the mouse?")

    opts.add_option("-B", "--button", action="store_true",
        dest="button", default=rfb.MOUSE_LEFT,
        help="Which button mask to click (0b1 - Left, 0b100 - Right)")
    
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
  
    if len(positionals) < 2:
        logger.error("Must provide X Y coordinates.")
        opts.print_help()
        sys.exit(-1)
    
        
    # start program
    main(options,positionals)