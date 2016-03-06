import optparse
import time
import sys


MB = 1<<20

def main(args=None):
    # get our args
    if args is None:
        args = sys.argv[1:]
        
    # Parse arguments
    opts = optparse.OptionParser()
    opts.add_option("-o", "--outputdir", action="store", type="string",
        dest="outputdir", default = ".",
        help="The directory that the files will be written to. (Default: CWD)")
    opts.add_option("-c", "--filecount", action="store", type="int",
         dest="filecount", default=1 , 
         help="The number of files to output. (Default: 1)")
    opts.add_option("-s", "--filesize", action="store", type="int",
        dest="filesize", default= 1024, 
        help="Size in bytes of files to be created. (Default 1024)")
    opts.add_option("-t", "--sleeptime", action="store", type="int",
        dest="sleeptime", default= 1, 
        help="Duration to sleep between file creations in seconds. (Default: 1s)")
    
    # Set our variables
    (options, positionals) = opts.parse_args(args)
    outputdir = options.outputdir
    filecount = options.filecount
    filesize = options.filesize
    sleeptime = options.sleeptime
    
    # Create the proper number of files
    for i in range(filecount):
        # Set our current filename
        newfile = outputdir+"/FILE"+str(i)
        
        
        print "Creating %s with size %d bytes"%(newfile,filesize,)
        f = open(newfile,'w+')
        f.write('A'*(filesize))
        f.close()
        time.sleep(sleeptime)

if __name__ == "__main__":
    main()
