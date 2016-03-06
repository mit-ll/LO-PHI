#!/usr/bin/env python
"""
    This is just a script to parse iozone output data from multiple runs and 
    aggregate all of it
    
    (c) 2015 Massachusetts Institute of Technology
"""

import argparse
import sys
import os
import numpy
import matplotlib
import scipy
matplotlib.use('GTKAgg') 
import matplotlib.pylab as pylab
import matplotlib.pyplot as plt


RECORD_LEN = 16384

def parse_iozone(filename):
    """
        Simple function to parse our output from iozone into a dict
    """
    
    iozone_struct = {"data":[]}
    
    f = open(filename,"r")
    
    # Read every file until we hit the rows with data            
    init = False
    for line in f:
        cols = line.split()
        
        if not init and len(cols) > 0 and cols[0] != 'KB':
            continue
        
        if len(cols) == 0:
            if init:
                break
            else:
                continue
        
        n = 8
        fix_cols = [line[i:i+n] for i in range(8, 8*5, n)]
        fix_cols += [line[8*5:8*5+9]]
        fix_cols += [line[8*5+9:8*5+9*2]]
        fix_cols += [line[i:i+n] for i in range(8*5+9*2, 8*5+9*2+8*3, n)]
        fix_cols += [line[i:i+9] for i in range(8*5+9*2+8*3,8*5+9*2+8*3+9*4, 9)]
        fix_cols += [line[118:118+8]]
        fix_cols += [line[126:126+9]]
        
        fix_cols = cols
        
        # First line is always the header
        if not init:
            
            iozone_struct['header'] = [x.strip() for x in fix_cols]
            init = True
        else:
            # Add all data to our list
            iozone_struct['data'].append([float(x) for x in fix_cols])
        
    f.close()
    
    return iozone_struct

def aggregate_data(input_dir):
    """
        Aggregate all of the data in a directory into one structure
    """
    iozone_data = []
    for (dirpath, dirnames, filenames) in os.walk(input_dir):
        for file in filenames:
            
            # Is this iozone output?
            if file.endswith("txt"):
                print "* Parsing %s..."%os.path.join(dirpath,file)
                
                data = parse_iozone(os.path.join(dirpath,file))
                iozone_data.append(data)
                
    aggregated_data = []
    # Aggregate all of our data
    init = False
    for id in iozone_data:
        aggregated_header = id['header']
        for x in range(len(id['data'])):
            tmp = []
            # Just summing our 2d array
            for y in range(len(id['data'][x])):
                # did we add this index yet, or is this the first?
                if x < len(aggregated_data) and y < len(aggregated_data[x]):
                    tmp.append( [id['data'][x][y]] + aggregated_data[x][y] )
                else:
                    tmp.append( [id['data'][x][y]] )
                
            # First entry or are we adding?
            if x < len(aggregated_data):
                aggregated_data[x] = tmp
            else:
                aggregated_data.append(tmp)
                
    return aggregated_data


def plot_data(data_without_orig,data_with_orig,title,x_axis,x_axis2,
              filename):
    
    data_without = []
    data_with = []
    for idx in range(len(data_without_orig)):
         
        avg = numpy.mean(data_without_orig[idx])
        data_without.append( data_without_orig[idx] / avg )
        data_with.append( data_with_orig[idx] / avg )
        
        
    index = numpy.arange(len(data_with))
      
    y_min = 1
    y_max = 1
    for row in data_without:
        if numpy.min(row) < y_min:
            y_min = numpy.min(row)
        if numpy.max(row) > y_max:
            y_max = numpy.max(row)
            
    for row in data_with:
        print numpy.min(row)
        if numpy.min(row) < y_min:
            y_min = numpy.min(row)
        if numpy.max(row) > y_max:
            y_max = numpy.max(row)    
                
    print (y_min,y_max)
    
    
    plt.figure()
    axes = plt.axes()
    
    
#     ax = fig.add_axes([0,len(data_without), y_min, y_max])
    
    plot_mean = axes.plot([numpy.average(x) for x in data_without],
               "-", 
               color="black",
               label='Uninstrumented Mean')
    
    axes.plot([numpy.max(x) for x in data_without],
             "+--", 
             color="black",
             label="Uninstrumented Max.")
    axes.plot([numpy.min(x) for x in data_without],
             ".--",
             color="black",
             label="Uninstrumented Min.")
     
    pylab.plot([numpy.mean(x) for x in data_with], "o")
     
    axes.errorbar(range(len(data_with)),
                   [numpy.mean(x) for x in data_with],
                   [numpy.std(x) for x in data_with],
                   fmt="o",
                   color="red",
                   label="With LO-PHI")
#     
    
#     axes.boxplot(data_with,
#                  sym='')
    
#     pylab.errorbar(range(len(read_data_with)),
#                    [numpy.mean(x) for x in data_without],
#                    [numpy.std(x) for x in data_without],
#                    fmt="k")

    plt.xlim(-1,len(x_axis))


    plt.title(title, fontsize=50)
    plt.ylabel("Normalized Throughput", fontsize=60)
    plt.xlabel("Total Size (KB) : Record Size(B)",labelpad=20, fontsize=60)
    
    plt.xticks(pylab.arange(len(x_axis)), x_axis, rotation=45)
#     

# #     axes2.spines['bottom']
    
#     axes.set_xticks(x_ticks,minor=False)
#     axes.set_xticklabels(x_axis)
#    axes.minorticks_on()
    plt.setp(axes)
    
    plt.tick_params(axis='x', which='major', labelsize=20)
    
    
    for key in x_axis2:
        plt.annotate(key, (x_axis2[key],0), (8, -25), 
                 xycoords='axes fraction', 
                 textcoords='offset points', 
                 va='top')
    
    plt.legend( 
               loc='upper right', 
               frameon=False,
               prop={'size':20})
    plt.show()
    
def plot_boxplot(data_without_orig, data_with_orig, labels, filename):
    
    data_without = []
    data_with = []
    
    print "Medians (%s):"%filename
    big_y = False
    for idx in range(len(data_with_orig)):
        
        median_without = numpy.median(data_without_orig[idx])
        median_with = numpy.median(data_with_orig[idx])
        
        if median_without/1000 > 1000:
            big_y = True
        print " * %d: With: %f, Without: %f"%(idx, median_with, median_without)
        prct_change = (median_without-median_with)/median_without
        print " * %d: Percent Change: %f"%(idx,prct_change)
#         data_without.append( data_without_orig[idx] / median_without )
#         data_with.append( data_with_orig[idx] / median_without )
        # convert to Megabyte/sec
        data_without_orig[idx] = [x/1000 for x in data_without_orig[idx]]
        data_with_orig[idx] = [x/1000 for x in data_with_orig[idx]]
        data_without.append( data_without_orig[idx] )
        data_with.append( data_with_orig[idx] )
    
    
    fig, ax1 = plt.subplots(figsize=(10,6))
    
    index = numpy.arange(len(data_without))+1
    bar_width=.1
    widths = numpy.ones(len(data_without))*bar_width*2
    bp = pylab.boxplot(data_without,
                  positions=index-bar_width,
                  widths=widths,
                  sym='')
    bp2 = pylab.boxplot(data_with,
                  positions=index+bar_width,
                  widths=widths,
                  sym='')
    
    plt.setp(bp['boxes'], color='black')
    plt.setp(bp['whiskers'], color='black')
    plt.setp(bp['fliers'], color='grey', marker='+')
    plt.setp(bp2['boxes'], color='black')
    plt.setp(bp2['whiskers'], color='black')
    plt.setp(bp2['fliers'], color='grey', marker='+')
    
    boxColors = ['white','grey']
    numBoxes = len(data_without)
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
    # Conver to KB
    labels = [int(x)/1024 for x in labels]
    plt.xticks(index, labels)
    plt.xlabel("File Size (MB)", fontsize=20)
    plt.ylabel("Disk Throughput (MB/sec)", fontsize=20)
    
    for tick in ax1.xaxis.get_major_ticks():
        tick.label.set_fontsize(15)
    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(15)
    
    # Labels
    if not big_y:
        plt.figtext(0.13, 0.18,  'Uninstrumented' ,
                    backgroundcolor=boxColors[0], color='black', weight='roman',
                    size=15,
                    bbox=dict(facecolor=boxColors[0], 
                              edgecolor='black', 
                              boxstyle='round,pad=1'))
        plt.figtext(0.35, 0.18, 'With Instrumentation',
                    backgroundcolor=boxColors[1],
                    color='white', weight='roman', size=15,
                    bbox=dict(facecolor=boxColors[1], 
                              edgecolor='black', 
                              boxstyle='round,pad=1'))
    else:
        plt.figtext(0.16, 0.18,  'Uninstrumented' ,
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
    plt.savefig(filename, format='eps', dpi=1000)


def aggregate_files(options):

    
    # Get our data with an without our sensor
    aggregated_data_without = aggregate_data(options.without_sensor_dir)
    aggregated_data_with = aggregate_data(options.with_sensor_dir)
    
    write_data_without_orig = []
    read_data_without = []
    x_axis = []
    x_axis2 = {}
    x_ticks = []
    labels = []
    
    idx = 0.0
    for row in aggregated_data_without:
        total_size = str(int(row[0][0]))
        x_axis.append( str(int(row[1][0])) )
        
        if int(row[1][0]) != RECORD_LEN:
            continue
        
        if total_size not in x_axis2:
            x_axis2[total_size] = idx/len(aggregated_data_without)
            x_ticks.append(idx)
            labels.append(total_size)
        
        idx += 1;
        
        write_data_without_orig.append(row[2])
        read_data_without.append(row[4])
        
    write_data_with_orig = []
    read_data_with = []
    for row in aggregated_data_with:
        if int(row[1][0]) != RECORD_LEN:
            continue
        
        write_data_with_orig.append(row[2])
        read_data_with.append(row[4])
        
            

     
#     f_scores = []
#     for x_with in  write_data_with:
#         for x_without in write_data_without:
#             var_with = scipy.var(x_with)
#             var_without = scipy.var(x_without)
#             F = var_with/var_without
#             df1 = len(x_with)
#             df2 = len(x_without)
#             print F
#             p_value = scipy.stats.f.cdf(F, df1, df2)
    
    plot_boxplot(write_data_without_orig, write_data_with_orig, labels,
                 "disk_write.eps")
    plot_boxplot(read_data_without, read_data_with, labels,
                 "disk_read.eps")

#     plot_data(data_without,
#                data_with,
#                "Write Throughput (Normalized to mean of uninstrumented system)",
#                x_axis,
#                x_axis2,
#                "write_throughput.ps")
#     
#     plot_data(read_data_without,
#                read_data_with,
#                "Read Throughput (Normalized to mean of uninstrumented system)",
#                x_axis,
#                x_axis2,
#                "read_throughput.ps")

    
    
            
    
            
        
                







if __name__ == "__main__":
    
     # Import our command line parser
    args = argparse.ArgumentParser()
 
#     args.add_argument("-t", "--target", action="store", type=str, default=None,
#                       help="Target for control sensor.  (E.g. 172.20.1.20 or VMName)")

    args.add_argument("without_sensor_dir", action="store", type=str, default=None,
        help="Directory with experiment output without our instrumentation.")
    
    # Add any options we want here
    args.add_argument("with_sensor_dir", action="store", type=str, default=None,
        help="Directory with experiment output done with our sensor.")
    
    
    
    
    # Get arguments
    options = args.parse_args()
    
    if options.without_sensor_dir is None:
        print "ERROR: Must provide input directory of data without instrumentation."
        sys.exit(0)
        
    if options.with_sensor_dir is None:
        print "ERROR: Must provide input directory of data WITH instrumentation."
        sys.exit(0)
        
    aggregate_files(options)