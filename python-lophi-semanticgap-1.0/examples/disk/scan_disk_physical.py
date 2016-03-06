#!/usr/bin/python
"""
    Module for scanning a disk when we only care about the NTFS partitions on it.

    (c) 2015 Massachusetts Institute of Technology
"""

# Native libs
import logging
import optparse
import os
import sys
import cPickle
import subprocess
import tempfile
import datetime

# 3d party libs
import pytsk3


logger = logging.getLogger(__name__)


def scan_disk(disk_url, scan_file_dir):
    """
    Scans a physical disk at disk_url, creates
    a scan file and saves it at scan_file_dir
    
    Scan file can be converted into a SemanticDiskEngine object, but only NTFS volumes will have any data at all,
    and only metadata.
    """

    # make the dir if it doesn't exist
    if not os.path.exists(scan_file_dir):
        os.makedirs(scan_file_dir)
    
    # open up the image
    img = pytsk3.Img_Info(url=disk_url)
    
    # get the volume info
    VOL_INFO = pytsk3.Volume_Info(img)


    # print out some info about the disk image
    logger.debug("--- Volume info ---")
    logger.debug("Current: %d" % VOL_INFO.current)
    logger.debug("VS Type: %d" % VOL_INFO.info.vstype)
    logger.debug("Offset: %d" % VOL_INFO.info.offset)
    logger.debug("Block Size: %d" % VOL_INFO.info.block_size)
    logger.debug("Endian: %d" % VOL_INFO.info.endian)
    logger.debug("Partition List: %s" % VOL_INFO.info.part_list)
    logger.debug("Parition Count: %d" % VOL_INFO.info.part_count)
    logger.debug("--- Volume info ---")


    # list of filenames we have to cat together at the end
    files = []

    sector_size = VOL_INFO.info.block_size

    part_number = 1

    sparse_number = 0
    
    copied_front_data = False

    # loop over each volume
    for vol in VOL_INFO:
        
        logger.debug("--- Partition ---")
        logger.debug("Start: %d" % vol.start)
        logger.debug("Length: %d" % vol.len)
        logger.debug("Description: %s" % vol.desc)
        logger.debug("Address: %d" % vol.addr)
        logger.debug("Flags: %d" % vol.flags)

        # ignore partition table at beginning
        if vol.addr == 0:
            continue

        # copy the MBR and other stuff if this is the unpartitioned space between 0
        # and the first partition

        if not copied_front_data:
            fname = save_front_data(disk_url, scan_file_dir, vol.start, vol.len*sector_size)
            files.append(fname)
            copied_front_data = True
            
            continue

        type = vol.desc.split(" ")[0]

        # if partition type is NTFS, do an NTFS clone on it
        if vol.desc == 'NTFS (0x07)':
            
            print "* Scanning %s (%d)..."%(disk_url,part_number)
            
            # Win 7 specific hack, so that we only have 1 sparse file.
            if vol.len == 204800 and vol.start == 2048:
                fname = save_NTFS_partition(part_number, disk_url, scan_file_dir, meta_only=False)
            else:
                fname = save_NTFS_partition(part_number, disk_url, scan_file_dir)
            files.append(fname)
            part_number += 1
            
        else:
            # create empty sparse file since we don't support other filesystems
            #fname = save_sparse(sparse_number, scan_file_dir, vol.len*sector_size)
            #files.append(fname)
            #sparse_number += 1
            pass
    
    
    
    # cat everything together
    logger.info("Cat everything together")
    filenames = " ".join(files)
    output_img = os.path.join(scan_file_dir, "disk.img")
    #cmd = "cat " + filenames + " > " + os.path.join(scan_file_dir, "disk.img")
    
    print "* Scan complete, merging scans into one file (%s)..."%output_img
    
    cmd = "cat " + filenames + " | cp --sparse=always /proc/self/fd/0 " + output_img
    
    logger.info("Running: %s" % cmd)
    
    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()

    logging.info("Changing permissions on '%s'"%output_img)

    os.chmod(output_img,0555)
        

def save_front_data(disk_url, scan_file_dir, vol_start, len_bytes):

    assert vol_start == 0
    
    logger.info("Saving front data.")
    
    output_fname = os.path.join(scan_file_dir, "front.img")
    input_f = open(disk_url, 'rb')
    output_f = open(output_fname, 'wb')
    output_f.write(input_f.read(len_bytes))
    
    input_f.close()
    output_f.close()

    return output_fname

def save_NTFS_partition(part_number, disk_url, scan_file_dir, meta_only=True):
    
    # volume name as device
    url = disk_url+str(part_number)
    
    # output file name
    out_filename = os.path.join(scan_file_dir, "ntfs"+str(part_number)+".img")
    
    if meta_only:
        cmd = "sudo ntfsclone --metadata -o \"%s\" %s" % (out_filename, url)
    else:
        cmd = "sudo ntfsclone -o \"%s\" %s" % (out_filename, url)
    logger.info("Saving NTFS partition.")
    logger.info("Running: %s" % cmd)
    
    # run an ntfsclone
    print subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
    
    # zip the image?

    return out_filename


def save_sparse(sparse_number, scan_file_dir, len_bytes):
    """
    Sparse files for unallocated space or unsupported filesystems
    """
    logger.info("Saving sparse data.")
    fname = os.path.join(scan_file_dir, "sparse"+str(sparse_number))
    f = open(fname, 'ab')
    f.truncate(len_bytes)
    f.close()
    
    return fname
    

        
def main(options):
    
    
    # Check our output directory
    OUTPUT_DIR = options.scan_file_dir
    if OUTPUT_DIR is None:
        OUTPUT_DIR = "lophi_scan_"+datetime.datetime.now().strftime("%m%d_%H%M")
        logger.warn("No output directory given, defaulting to timestamp. (%s)"%OUTPUT_DIR)
    
    if os.path.exists(OUTPUT_DIR):
        logger.error("Output directory %s already exist."%OUTPUT_DIR)
        return
    
    # Check out input drive
    DRIVE_PREFIX = "/dev/"
    SCAN_DISK = options.disk_url
    
    # If no disk was defined on the command line, go interactive
    if SCAN_DISK == "":
        # Get list of all drives mounted
        devices = os.listdir(DRIVE_PREFIX)
        drives = {}
        for d in devices:
            if d.startswith("sd") and d[-1].isdigit() and not d.startswith("sda"):
                path = os.path.join(DRIVE_PREFIX, d)
                
                # Do we already have a list of partitions for this drive?
                if path[:-1] not in drives:
                    drives[path[:-1]] = []
                    
                # add this parition to the list of drives
                drives[path[:-1]].append(path) 

        if len(drives) == 0:
            print "** No drives other than sda were found on this system.  (Are you sure that it is connected properly?)"
            return
        
        # Print drives to user
        print "Please select a drive to scan"
        print ""
        idx = 0
        for d in drives.keys():
            print "  %d : %s  (%d mounted partitions)" % (idx, d, len(drives[d]))
            idx += 1
        print ""
        # Get user input
        user_input = -1
        while user_input < 0 or user_input >= len(drives):
            
            # Let the user select a drive 
            if len(drives) == 1:
                user_input = int(raw_input("Drive Selection [0]:" ))
            else:
                user_input = int(raw_input("Drive Selection [0-%d]:" % (
                                                            len(drives) - 1)))
            
            # If there is only one choice just default it
            if user_input == "" and len(drives) == 1:
                user_input = drives[0]

        SCAN_DISK = drives.keys()[user_input]
        
        for mount in drives[SCAN_DISK]:
            subprocess.Popen("umount "+mount, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    print "* Output directory set to: %s" % OUTPUT_DIR
    print "* Scan disk set to: %s" % SCAN_DISK
    
    if not os.path.exists(SCAN_DISK):
        logger.error("Disk %s does not exist."%SCAN_DISK)
        return
    
    print "-"
    
    
    # Scan our drive into our output directory!
    scan_disk(SCAN_DISK, OUTPUT_DIR)
    
    print "** Done!"


if __name__ == "__main__":
    
    
    # Ensure that we are root
    if not os.geteuid() == 0:
        print "You aren't root.  Goodbye."

        sys.exit(0)
    
    # Import our command line parser
    opts = optparse.OptionParser()

   
    # disk
    opts.add_option("-i", "--disk_url", action="store", type="string",
        dest="disk_url", default="",
        help="Path to where the disk is")

    # Directory where we store scan file
    opts.add_option("-o", "--output_dir", action="store", type="string",
        dest="scan_file_dir", default=None,
        help="Directory to store scan file data")


    # Debug
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

    
    main(options)
