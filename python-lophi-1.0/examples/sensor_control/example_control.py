#!/usr/bin/env python
"""
    Example script for interacting with control sensors

    (c) 2015 Massachusetts Institute of Technology
"""
#  Native
import os
import sys
import optparse
import logging
import time

# LO-PHI
import lophi.globals as G
from lophi import command_line
from lophi.actuation.keypressgenerator import KeypressGeneratorPhysical,KeypressGeneratorVirtual
from lophi.sensors.control.physical import ControlSensorPhysical
from lophi.sensors.control.virtual import ControlSensorVirtual

def main(options):
    
    # Define our control sensor and parser
    if options.sensor_type == G.MACHINE_TYPES.PHYSICAL:
        control_sensor = ControlSensorPhysical(options.target,options.port)
        parser = KeypressGeneratorPhysical()
    else:
        control_sensor = ControlSensorVirtual(options.target,vm_type=options.sensor_type)
        parser = KeypressGeneratorVirtual()
     
    if options.status:
        print "Getting status of machine..."
        print "Status:", control_sensor.power_status()
        
    elif options.shutdown:
        print "Shutting down machine..."
        control_sensor.power_shutdown()
        
    elif options.poweron:
        print "Starting machine..."
        control_sensor.power_on()
        
    elif options.poweroff:
        print "Turing off machine..."
        control_sensor.power_off()
    
    elif options.reset:
        print "Resetting machine..."
        control_sensor.power_reset()
        
    elif options.reboot:
        print "Rebooting machine..."
        control_sensor.power_reboot()
        
    elif options.mouse_click:
        (x,y) = options.mouse_click.split(",")
        x = int(x)
        y = int(y)
        print "Sending mouse click to (%d,%d)"%(x,y)
        control_sensor.mouse_click(x, y)
        
    elif options.script:
        print "Running script %s on machine..."%options.script
        if not os.path.exists(options.script):
            logging.error("File (%s) does not exist!" % options.script)
            sys.exit(0)
    
        # open file
        f = open(options.script, 'r')
        script_text = f.read()
        f.close()
        
        script = parser.text_to_script(script_text)
        
        control_sensor.keypress_send(script)

    elif options.mouse_wiggle is not None:
        control_sensor.mouse_wiggle(options.mouse_wiggle)
    else:
        print "No action taken."
        opts.print_help()
    

if __name__ == "__main__":
    
    opts = optparse.OptionParser()

    # Port
    opts.add_option("-p", "--port", action="store", type="string",
        dest="port", default=G.SENSOR_CONTROL.DEFAULT_PORT,
        help="control_sensor port (Default: %s)"%G.SENSOR_CONTROL.DEFAULT_PORT)
    # Power off
    opts.add_option("-S", "--shutdown", action="store_true",
        dest="shutdown", default=False,
        help="Shutdown machine")
    # Power on
    opts.add_option("-O", "--poweron", action="store_true",
        dest="poweron", default=False,
        help="Power on machine")
    # Reset
    opts.add_option("-R", "--reset", action="store_true",
        dest="reset", default=False,
        help="Reset machine")
    # Reboot
    opts.add_option("-B", "--reboot", action="store_true",
        dest="reboot", default=False,
        help="Reboot machine")
    # Power off
    opts.add_option("-F", "--poweroff", action="store_true",
        dest="poweroff", default=False,
        help="Power off machine")
    
    # Keypress script
    opts.add_option("-s", "--script", action="store", type="string",
        dest="script", default=None,
        help="Keypress script (E.g. hello_physical.act)")
    
    # Mouse click
    opts.add_option("-m", "--mouse_click", action="store", type="string",
                    dest="mouse_click", default=None,
                    help="Send a mouse click to x,y (E.g -m 100,100)")

    opts.add_option("-w","--mouse_wiggle",action="store",type="int",
                    dest="mouse_wiggle", default=None,
                    help="Wiggle the mouse (0 or 1)")
    
    # Status
    opts.add_option("-q", "--status", action="store_true",
        dest="status", default=False,
        help="Power status of machine machine")

    # parse user arguments
    command_line.parser(opts, main)
