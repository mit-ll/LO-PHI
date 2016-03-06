#!/usr/bin/python

# Native
import os
import sys
import optparse
import logging

logging.basicConfig(level=logging.DEBUG)

# Append our system path
sys.path.append(os.path.join(os.getcwd(), "../../"))


# LO-PHI Classes
from lophi.sensors.disk.physical import DiskSensorPhysical

# Globals
PHY_HOST = "172.20.1.1"

def main(args=None):
    """
        Very simple toy program to interaction with our disk sensor
    """

    opts = optparse.OptionParser()

    opts.add_option("-p", "--physicalhost", action="store", type="string",
        dest="physicalhost", default=PHY_HOST,
        help="Physical Host IP (Default: %s)" % PHY_HOST)

    opts.add_option("-o", "--operation", action="store", type="int",
        dest="operation", default=0x0,
        help="operation:\n\t0x00 - READ\n\t0x01 - WRITE\n\t0x80 - SATA")


    opts.add_option("-m", "--memory_address", action="store", type="int",
        dest="memory_address", default=0,
        help="2 byte memory address (Ex. 0x0000)")

#    opts.add_option("-l", "--memory_length", action="store", type="int",
#        dest="memory_length", default=0,
#        help="number of d-words to write")

    opts.add_option("-d", "--data", action="store", type="string",
        dest="data", default="\x00\x00\x00\x00",
        help="String of data that we want to send. (Ex. \"\\x00\\x00\\x00\\x01\")Make sure to be word aligned!")

    opts.add_option("-l", "--length", action="store", type="int",
        dest="length", default=None,
        help="Set the length field. (This will override the automatic calculation based on the data.)")

    opts.add_option("-c", "--count", action='store', type="int",
                    dest='count', default=1,
                    help="Number of times to send command")

    opts.add_option("-P", "--print_all_regs", action='store', type="int",
                    dest='print_regs', default=1,
                    help="Number of times to send command")

    (options, positionals) = opts.parse_args(args)


    """
        Start sensor code
    """


    # What kind of client do we need?
    print "Initalizing Physical client at %s..." % options.physicalhost
    disk_sensor = DiskSensorPhysical(options.physicalhost)

    # Connect to host
    disk_sensor._connect()

    # Decode our data
    data = None
    if options.data is not None:
        data = options.data.decode('string_escape')

    length = options.length

    # Send our command
    for i in range(options.count):
        packet = disk_sensor._send_command(options.operation,
                               options.memory_address,
                               data, length=length)
        print "Response:"
        print packet
        
    disk_sensor.print_all_registers()

    disk_sensor._disconnect()


if __name__ == "__main__":
    main()
