"""
    This is an example of using volatility with our sensors to click buttons

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import optparse
import sys
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G
from lophi.sensors.control.physical import ControlSensorPhysical
from lophi.sensors.control.virtual import ControlSensorVirtual

from lophi_semanticgap.memory.volatility_extensions import ButtonClicker


def main(options, positionals):
    
    # Define our host type
    if options.sensor_type != G.MACHINE_TYPES.PHYSICAL:
        vol_host = "vmi://"+options.target
        control_sensor = ControlSensorVirtual(options.target,vm_type=options.sensor_type)
    else:
        if options.memory_sensor is None:
            logger.error("You must provide an ip for the memory sensor.")
            return
        vol_host = "lophi://"+options.memory_sensor
        control_sensor = ControlSensorPhysical(options.target)
    # What profile are we looking at?
    vol_profile = options.profile
        
    # Initialize volatility
    bc = ButtonClicker(vol_host,
                       vol_profile,
                       '2147483648', #2GB
                       control_sensor)

    clicked = bc.click_buttons(options.process)
    
    for c in clicked:
        print "* Clicked: %s:%s"%(c['process'],c['name'])


                    
                    
if __name__ == "__main__":
    
    opts = optparse.OptionParser()
    
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
    
    opts.add_option("-m", "--memory_sesnor", action="store", type="string",
        dest="memory_sensor", default=None,
        help="IP address of physical memory sensor. (Only applicable for physical introspection)")

    opts.add_option("-p", "--profile", action="store", type="string",
                    dest="profile", default="WinXPSP3x86",
                    help="Volatility profile")
    
    opts.add_option("-P", "--process", action="store", type="string",
                    dest="process", default=None,
                    help="Only click buttons for a specific process. (e.g. explorer.exe)")
    
    opts.add_option("-d", "--debug", action="store_true",
        dest="debug", default=False,
        help="Enable DEBUG")
    
    
    
    # Get arguments
    (options, positionals) = opts.parse_args(None)
   
    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        
    # What sensor type are we initializing?
    if options.sensor_type is None:
        logger.error("Please specify a sensor type.")
        opts.print_help()
        sys.exit(0)
   
    # Is a target defined?
    # What sensor type are we initializing?
    if options.target is None:
        logger.error("Please specify a target.")
        opts.print_help()
        sys.exit(0)
    
    main(options, positionals)
