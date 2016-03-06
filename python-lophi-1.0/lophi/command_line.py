"""
    This is intended ot be imported by other scripts to handle a lot of the 
    default command line options

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import logging
import sys
import os
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G

def parser(opts, callback, args=None):

    # Get our machine types
    machine_types = {}
    for x in G.MACHINE_TYPES.__dict__:
        if x != "ASCII" and not x.startswith("_"):
            machine_types[x] = G.MACHINE_TYPES.__dict__[x]

    # Comand line options
    opts.add_option("-t", "--target", action="store", type="string",
        dest="target", default=None,
        help="IP address of physical card or name of VM to attach to.")
    
    opts.add_option("-T", "--type", action="store", type="int",
        dest="sensor_type", default=None,
        help="Type of sensor. %s"%machine_types)

    opts.add_option("-d", "--debug", action="store_true",
        dest="debug", default=False,
        help="Enable DEBUG")
    
    # Get arguments
    (options, positionals) = opts.parse_args(args)
   
    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    # What sensor type are we initializing?
    if options.sensor_type is None:
        logger.error("Please specify a sensor type.")
        opts.print_help()
        return
   
    # Is a target defined?
    # What sensor type are we initializing?
    if options.target is None:
        logger.error("Please specify a target.")
        opts.print_help()
        return
   

        
    # Call our callback function
    callback(options)
