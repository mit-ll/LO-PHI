#!/usr/bin/env python
"""
    Example script for reading memory using the memory sensors

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import sys
import os
import optparse
import time
import logging
logger = logging.getLogger(__name__)

# Ensure that we can still run it from the command line if we want
sys.path.append(os.path.join(os.getcwd(), "../../"))
sys.path.append(os.path.join(os.getcwd(), "../"))

# LO-PHI
import lophi.globals as G
from lophi import command_line
from lophi.sensors.memory.physical import MemorySensorPhysical
# from lophi.sensors.memory.physical_old import MemorySensorPhysical
from lophi.sensors.memory.virtual import MemorySensorVirtual
from lophi.capture import CaptureWriter, CaptureReader
from lophi.data import MemorySensorPacket


def str_to_hex(string):
    return "".join("{0:x}".format(ord(c)) for c in string)

default_ip = "172.20.1.3"
default_output = "memory_dump"
default_read_size = (32 * 1024) # 32K
default_chunk_size = 512
default_startaddr = 0x00000000


def main(options):    

    if options.replay_file is not None:
        cap_reader = CaptureReader(options.replay_file)
         
        for (ts, data) in cap_reader:
            print "Time: ", ts, "s"
            print MemorySensorPacket(data)
            
        return

    if options.sensor_type == G.MACHINE_TYPES.PHYSICAL:
        client = MemorySensorPhysical(options.target, 
                                      cache_timeout=0,
                                      use_threading=False)
    else:
        client = MemorySensorVirtual(options.target)

    READ_SIZE = int(options.read_size)
    start_addr = options.startaddr   
        
    # Create our output file
    try:
        os.makedirs(os.path.dirname(options.output))
    except:
        pass

    try:
        mcap_writer = None
        if options.loop_forever == True:
            logger.debug("Creating capture file.")
            options.output += ".mcap"
            mcap_writer = CaptureWriter(options.output)
            mcap_writer.start()
        else:
            logger.debug("Creating dump file.")
            options.output += ".mfd"
            output_file = open(options.output, "w+")
    except:
        print "ERROR: Could not open output file."
        sys.exit(0)

    # Read memory
    count = 0
    start = time.time()
    sensor_packet = MemorySensorPacket()
   
    while True:
        
        try:
            # Get memory from remote system
               
            # Read memory
            data = client.read(start_addr, READ_SIZE)
     
            # Write to file?
            if not options.loop_forever:
                output_file.write(data)
            else:
                sensor_packet.address = start_addr
                sensor_packet.data = data
                sensor_packet.length = READ_SIZE
                mcap_writer.put(sensor_packet)
    
            # Just read once?
            if not options.loop_forever:
                break
            else:
                print "Completed read #%d"%count
                count += 1
        except:
            # Just finish up
            break
    end = time.time()
    
    # Do we have an mcap file to close?
    if mcap_writer is not None:
        mcap_writer.stop()
    else:
        # Close output file
        output_file.close()

    print "Memory dump (%d bytes) written to %s. Took %s seconds." % (len(data),options.output,end-start)




if __name__ == "__main__":


    opts = optparse.OptionParser()

    # Add our options
    opts.add_option("-o", "--output", action='store', type="string",
                    help="Output file to save memory dump to. (Default: %s)"%default_output,
                    default=default_output, dest='output')
    opts.add_option("-a", "--start_addr", action='store', type="int",
                    help="Start address to start reading from. (Default 0x%08x)"%default_startaddr,
                    default=default_startaddr, dest='startaddr')

    opts.add_option("-s", "--read_size", action='store', type="int",
                    help="Number of bytes to read. (Default: %d bytes)"%default_read_size,
                    default=default_read_size, dest='read_size')

    opts.add_option("-L", "--loop_forever", action="store_true",
                    dest="loop_forever", default=False,
                    help="Instead of dumping to file, just read that region forever. (Default: False)")

    opts.add_option("-R", "--replay_file", action="store", type="string",
        dest="replay_file", default=None,
        help="Read input from file instead of actual sensor.")
    
    
    
    # parse user arguments
    command_line.parser(opts, main)
