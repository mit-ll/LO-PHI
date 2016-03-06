"""
    This is a simple test script to enumerate the read rate of our memory 
    sensor.
    
    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import optparse
import os
import sys
import time
import logging
logger = logging.getLogger(__name__)

# LO-PHI
from lophi.sensors.memory.physical import MemorySensorPhysical


def str_to_hex(string):
    return "".join("{0:x}".format(ord(c)) for c in string)

default_ip = "172.20.1.3"
default_read_size = 7680
default_startaddr = 0x00000000


def main(options):
    """
        Read the specified memory region and record statistics
    """

    # Initilize our experiment
    client = MemorySensorPhysical(options.target, 
                                      cache_timeout=0,
                                      use_threading=True)
    READ_SIZE = int(options.read_size)*85
    start_addr = options.startaddr   
        
    # Read memory
    offset = 0
   
    read_rates = []
    total_read = 0
    count = 0
    
    output = open(options.output_file, "w+")
    output.write("Memory Address,Bytes Read,Time Elapsed,Bytes/Second\n")

    for addr in xrange(start_addr,2**30, READ_SIZE):
        
        try:

            time_start = time.time()
            data = client.read(addr, READ_SIZE)
            time_elapsed = (time.time() - time_start)
            
            total_read += len(data)
            count += 1

            rate = (len(data)/time_elapsed)
            print "Addr: 0x%08X,  Read: %d bytes, %f bytes/sec" % (addr,
                                                                   len(data),
                                                                   rate)
            output.write("0x%08X,%d,%f,%f\n" % (addr, len(data), time_elapsed,
                                                rate))
            read_rates.append(rate)

        except:
            import traceback
            traceback.print_exc()
            # Just finish up
            break
        
    output.close()
    

if __name__ == "__main__":

    # Import our command line parser
    opts = optparse.OptionParser()

    opts.add_option("-a", "--start_addr", action='store', type="int",
                    help="Start address to start reading from. (Default "
                         "0x%08x)" % default_startaddr,
                    default=default_startaddr, dest='startaddr')

    opts.add_option("-s", "--read_size", action='store', type="int",
                    help="Number of bytes to read. (Default: %d bytes)" %
                         default_read_size,
                    default=default_read_size, dest='read_size')

    opts.add_option("-o", "--output_file", action='store', type='string',
                    default="memory_speed.txt",
                    help="Name of output file for results.")

    # Comand line options
    opts.add_option("-t", "--target", action="store", type="string",
                    dest="target", default="172.20.1.11",
                    help="IP address of physical card or name of VM to "
                         "attach to.")

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
   
    # Does our output file exist?
    if os.path.exists(options.output_file):
        logger.error("Output file (%s) already exists." % options.output_file)
        opts.print_help()
        sys.exit(0)
   
    # Is a target defined?
    if options.target is None:
        logger.error("Please specify a target.")
        opts.print_help()
        sys.exit(0)
        
    main(options)
