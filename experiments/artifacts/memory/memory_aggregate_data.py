#!/usr/bin/env python
"""
    This is a script to aggregate data from ramspeed
        
    (c) 2015 Massachusetts Institute of Technology
"""

import argparse
import sys
import os
import numpy

import matplotlib
matplotlib.use('GTKAgg') 
import matplotlib.pyplot as plt


def parse_ramspeed(filename):
    """
        Simple function to parse our output from ramspeed into a dict
    """
    
    ramspeed_struct = {}
    
    f = open(filename,"r")
    
    # Read every file until we hit the rows with data            
    init = False
    
    empty_count = 0
    for line in f:
        # Ignore header data
        if line.strip() == "":
            empty_count += 1
            continue  
        if empty_count < 3:  
            continue
        
        cols = line.split()
        
        # Ensure it's a valid line
        if len(cols) < 3:
            continue
        
        # Extract values
        mem_operation = cols[0]
        mem_type = cols[1].strip(":")
        if mem_type == "BatchRun":
            continue
        
        mem_rate = float(cols[2])
        
        # Store in our nested structure
        if mem_operation not in ramspeed_struct:
            ramspeed_struct[mem_operation] = {}
            
        if mem_type not in ramspeed_struct[mem_operation]:
            ramspeed_struct[mem_operation][mem_type] = [mem_rate]
        else:
            ramspeed_struct[mem_operation][mem_type].append(mem_rate)
        
    f.close()
    
    return ramspeed_struct

def parse_data_rate(filename):
    f = open(filename,"r")
    s = f.read()
    s_list = s.split("\t")
    f.close()
    
    time_elapsed = float(s_list[0])
    bytes = float(s_list[1])
    
    return bytes/time_elapsed


def parse_dir(input_dir):
    # parse all of our files
    ramspeed_data = []
    data_rate_list = []
    for (dirpath, dirnames, filenames) in os.walk(input_dir):
        for file in filenames:
            
            # Is this iozone output?
            if file.endswith("txt"):
                print "* Parsing %s..."%file
                if file.find("sensor") != -1:
                    rate = parse_data_rate(os.path.join(dirpath,file))
                    data_rate_list.append(rate)
                else:
                    data = parse_ramspeed(os.path.join(dirpath,file))
                    ramspeed_data.append(data)
                
    data_rate = numpy.average(data_rate_list)/(1.0*10**6)
    print "Data Rate: ", data_rate, "MB/sec"
    
    # Aggregate data into one big struct
    aggregate_data = {}
    for rd in ramspeed_data:
        for mem_operation in rd:
            if mem_operation in aggregate_data:
                for mem_type in rd[mem_operation]:
                    if mem_type in aggregate_data[mem_operation]:
                        aggregate_data[mem_operation][mem_type] += rd[mem_operation][mem_type]
                    else:
                        aggregate_data[mem_operation][mem_type] = rd[mem_operation][mem_type]
            else:
                aggregate_data[mem_operation] = {}
                for mem_type in rd[mem_operation]:
                    aggregate_data[mem_operation][mem_type] = rd[mem_operation][mem_type]
                    
    return (aggregate_data, data_rate_list)


def extract_graph_data(aggregate_data):
    
    rate_data = {}
    for mem_operation in aggregate_data:
        for mem_type in aggregate_data[mem_operation]:
            rates = aggregate_data[mem_operation][mem_type]
            if mem_type != "AVERAGE":
                continue
            print "Operation: %s, Type: %s"%(mem_operation,mem_type)
            print " Avg: %f, StDev: %f, Count: %d"%(numpy.average(rates),
                                                    numpy.std(rates),
                                                    len(rates))            
            rate_data[mem_operation] = rates
            
    return rate_data

 
def aggregate_files(options):


    # Get aggregate data from input 1
    aggregate_data_sensor, data_rate_list1 = parse_dir(options.input_dir_sensor)
    aggregate_data_base, data_rate_list2 = parse_dir(options.input_dir_base)
    
    # Extract the data to graph
    rate_data_sensor = extract_graph_data(aggregate_data_sensor)
    rate_data_base = extract_graph_data(aggregate_data_base)

    
#     f = open("tmp.csv", "w+")
#     for x in range(100):
#         tmp_list = []
#         for y in range(len(rate_data_sensor)):
#             print y,x
#             tmp_list.append(str(rate_data_sensor[y][x]))
#         f.write(",".join(tmp_list)+"\n")
#         
#     f.close()

#     figure()

    
    fig, ax1 = plt.subplots(figsize=(10,6))
    
    plot_data_sensor = []
    plot_data_base = []
    labels = []
    for mem_operation in ['SSE','MMX','INTEGER','FL-POINT']:
        # Output medians
        median_without = numpy.median(rate_data_base[mem_operation])
        median_with = numpy.median(rate_data_sensor[mem_operation])
        
        stdev_without = numpy.std(rate_data_base[mem_operation])
        stdev_with = numpy.std(rate_data_sensor[mem_operation])
        
        print " * %s: With: %f, Without: %f"%(mem_operation, median_with, 
                                              median_without)
        print " * %s: With (Stdev): %f, Without (Stdev): %f"%(mem_operation,
                                                              stdev_with, 
                                                              stdev_without)
        prct_change = (median_without-median_with)/median_without
        print " * %s: Percent Change: %f"%(mem_operation,prct_change)
        
        labels.append(mem_operation)
        plot_data_base += [rate_data_base[mem_operation]]
        plot_data_sensor += [rate_data_sensor[mem_operation]]
    
    index = numpy.arange(len(rate_data_sensor))+1
    bar_width=.2
    widths = numpy.ones(len(rate_data_sensor))*bar_width*2
    print index
    
    bp = plt.boxplot(plot_data_base,
                     positions=index-bar_width,
                     widths=widths,
                     sym='')
    bp2 = plt.boxplot(plot_data_sensor,
                     positions=index+bar_width,
                     widths=widths,
                     sym='')
    
    # Color bps
    plt.setp(bp['boxes'], color='black')
    plt.setp(bp['whiskers'], color='black')
    plt.setp(bp['fliers'], color='grey', marker='+')
    plt.setp(bp2['boxes'], color='black')
    plt.setp(bp2['whiskers'], color='black')
    plt.setp(bp2['fliers'], color='grey', marker='+')
    
    boxColors = ['white','grey']
    numBoxes = len(rate_data_sensor)
    medians = range(numBoxes)
    
    for i in range(numBoxes):

        # Box 1
        box = bp['boxes'][i]
        boxX = []
        boxY = []
        for j in range(5):
            boxX.append(box.get_xdata()[j])
            boxY.append(box.get_ydata()[j])
        boxCoords = zip(boxX,boxY)
        # Alternate between Dark Khaki and Royal Blue
        k = i % 2
        boxPolygon = plt.Polygon(boxCoords, facecolor=boxColors[0])
        ax1.add_patch(boxPolygon)
        # Now draw the median lines back over what we just filled in
        med = bp['medians'][i]
        medianX = []
        medianY = []
        for j in range(2):
            medianX.append(med.get_xdata()[j])
            medianY.append(med.get_ydata()[j])
            plt.plot(medianX, medianY, 'k')
            medians[i] = medianY[0]
            
        # Box 2
        box = bp2['boxes'][i]
        boxX = []
        boxY = []
        for j in range(5):
            boxX.append(box.get_xdata()[j])
            boxY.append(box.get_ydata()[j])
        boxCoords = zip(boxX,boxY)
        # Alternate between Dark Khaki and Royal Blue
        boxPolygon = plt.Polygon(boxCoords, facecolor=boxColors[1])
        ax1.add_patch(boxPolygon)
        # Now draw the median lines back over what we just filled in
        med = bp2['medians'][i]
        medianX = []
        medianY = []
        for j in range(2):
            medianX.append(med.get_xdata()[j])
            medianY.append(med.get_ydata()[j])
            plt.plot(medianX, medianY, 'k')
            medians[i] = medianY[0]


    
    plt.grid('on')
    plt.xlim(0,len(labels)+1)
    plt.xticks(index, labels)
    plt.xlabel("Memory Operation Type", fontsize=20)
    plt.ylabel("Memory Throughput (MB/sec)", fontsize=20)
    
    
    for tick in ax1.xaxis.get_major_ticks():
        tick.label.set_fontsize(15)
    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(15)
    
#     plt.title(options.title)
#     rate_data_base  = [[]] + rate_data_base
#     plt.boxplot(rate_data_base)

    plt.figtext(0.15, 0.18,  'Uninstrumented' ,
                backgroundcolor=boxColors[0], color='black', weight='roman',
                size=15,
                bbox=dict(facecolor=boxColors[0], 
                          edgecolor='black', 
                          boxstyle='round,pad=1'))
    plt.figtext(0.38, 0.18, 'With Instrumentation',
                backgroundcolor=boxColors[1],
                color='white', weight='roman', size=15,
                bbox=dict(facecolor=boxColors[1], 
                          edgecolor='black', 
                          boxstyle='round,pad=1'))

#     plt.show()
    plt.tight_layout()
    plt.savefig(options.output_filename, format='eps', dpi=1000)

if __name__ == "__main__":
    
    # Import our command line parser
    args = argparse.ArgumentParser()
 
#     args.add_argument("-t", "--target", action="store", type=str, default=None,
#                       help="Target for control sensor.  (E.g. 172.20.1.20 or VMName)")
    
    # Add any options we want here
    args.add_argument("input_dir_sensor", action="store", type=str, default=None,
        help="Directory with experiment output.")
    
    args.add_argument("input_dir_base", action="store", type=str, default=None,
        help="Directory with experiment output.")
    
    args.add_argument("-t", "--title", action="store", type=str, default=None,
                      help="Title of graph")
    
    args.add_argument("-o", "--output_filename", action="store", type=str, 
                      default=None, help="Output filename")
    
    # Get arguments
    options = args.parse_args()
    
    if options.input_dir_sensor is None or options.input_dir_base is None:
        print "ERROR: Must provide input directory"
        args.print_help()
        sys.exit(0)
        
#     if options.title is None:
#         print "ERROR: Must provide a title."
#         args.print_help()
#         sys.exit(0)
        
    if options.output_filename is None:
        print "ERROR: Must provide an output filename."
        args.print_help()
        sys.exit(0)
        
    aggregate_files(options)