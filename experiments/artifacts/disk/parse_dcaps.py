#!/usr/bin/env python
"""
    Script to parse dcap files for graphs

    (c) 2015 Massachusetts Institute of Technology
"""
import argparse
import sys
import os
from collections import deque

from lophi.capture import CaptureReader

def parse_dcap(filename):
    
    reader = CaptureReader(filename)
    
    start = None
    end = None
    
    data_size = 0
    
    window_data = deque([])
    window_time = deque([])
    window_sum = 0
    max_throughput = 0
    for (ts,data) in reader:
        
        data_size += len(data)
        
        # Keep track of timestamps
        if start is None:
            start = ts
        end = ts
            
        window_sum += len(data)
        window_data.append(len(data))
        window_time.append(ts)
        
        # Only compute with a certain number of samples
        if len(window_data) >= 10000 and window_time[-1] != window_time[0]:

            throughput = window_sum/(window_time[-1]-window_time[0])

            if throughput > max_throughput:
                max_throughput = throughput
        
        while len(window_data) >= 1000 and window_time[-1] != window_time[0]:
            data_remove = window_data.popleft()
            window_sum -= data_remove
            window_time.popleft()

    elapsed_time = end-start
    
    print "Time elapsed: ",elapsed_time
    print "Bytes Read: ",data_size
    print "Avg Rate: ", (data_size/elapsed_time)
    print "Max Rate: ", max_throughput


def parse_dcaps(directory):
    
    for (dirpath, dirnames, filenames) in os.walk(directory):
        for file in filenames:
            
            # Is this iozone output?
            if file.endswith("dcap"):
                print "* Parsing %s..."%file
                parse_dcap(os.path.join(dirpath, file))
                
                
if __name__ == "__main__":
    
    # Import our command line parser
    args = argparse.ArgumentParser()

    args.add_argument("dcap_dir", action="store", type=str, default=None,
        help="Directory containting dcap files.")
    
        # Get arguments
    options = args.parse_args()
    
    if options.dcap_dir is None:
        print "ERROR: Must provide input directory with dcaps."
        sys.exit(0)
        
    parse_dcaps(options.dcap_dir)