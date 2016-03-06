"""
   Wrapper script for IOZONE on Windows
"""


import math
import subprocess
import time

record_size = '64K'
file_size = '2G'
iozone_cmd = "iozone.exe -i 0 -i 1 -s %s -r %s" % (file_size, record_size)

def mean_std_dev(lst):

    if (len(lst) <= 1):
        if lst:
            return lst[0], 0
        else:
            return 0, 0

    mean = sum(lst)/float(len(lst))

    std_dev = 0

    for num in lst:
        std_dev += (num - mean)**2
    std_dev = math.sqrt(std_dev/float(len(lst)-1))

    return mean, std_dev


def main(args=None):

    import optparse
    opts = optparse.OptionParser()

    opts.add_option("-r", "--runs", action="store", type="int",
                    dest="runs", default=1, help="Times to run benchmark.")

    (options, ars) = opts.parse_args(args)


    # lists for storing results
    writes = []
    rewrites = []
    reads = []
    rereads = []

    # run for options.runs times

    print time.strftime('%X %x %Z') + " Running Iozone Benchmark cmd: " + iozone_cmd
    print "%d trials." % options.runs

    for i in range(options.runs):

        r = subprocess.check_output(iozone_cmd)

        r = r.split('\n')
        
        #print r[-4]
        #print r[-3]
    
        r = r[-4].strip().split()

        writes.append(float(r[2]))
        rewrites.append(float(r[3]))
        reads.append(float(r[4]))
        rereads.append(float(r[5]))


    # compute avg and std devs

    avg_write, std_write = mean_std_dev(writes)
    avg_rewrite, std_rewrite = mean_std_dev(rewrites)
    avg_read, std_read = mean_std_dev(reads)
    avg_reread, std_reread = mean_std_dev(rereads)

    # print results

    print ""
    print time.strftime('%X %x %Z') + " Benchmark complete."
    print "Record Size: " + record_size
    print "File Size: " + file_size
    print "Runs: %d" % options.runs
    print ""

    print "Write Throughput (Kb/s):   %f avg, %f std dev" % (avg_write, std_write)
    print "Rewrite Throughput (Kb/s): %f avg, %f std dev" % (avg_rewrite, std_rewrite)
    print "Read Throughput (Kb/s):    %f avg, %f std dev" % (avg_read, std_read)
    print "Reread Throughput (Kb/s):  %f avg, %f std dev" % (avg_reread, std_reread)
    

if __name__=="__main__":

    main()

    
