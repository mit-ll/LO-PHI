#!/usr/bin/env python

"""
    Memory and Disk Noise Filter

    (c) 2015 Massachusetts Institute of Technology
"""


# Native
import argparse
import os
import pickle
import pprint
import sys
import logging
logger = logging.getLogger(__name__)

# LO-PHI

from lophi_analysis.analysis_filter import DiskFilter
from disk_analysis import DiskAnalysis

def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not args.output_path:
        logger.error("Please specify a filename to save the filters to.")
        sys.exit(0)

    # for now, process local directory
    if args.dir_path:
        logger.info("Analyzing all analyses in directory %s" % (args.dir_path))


        # Disk
        disk_filter = DiskFilter()

        for analysis_dir in os.listdir(args.dir_path):
            path = os.path.join(args.dir_path, analysis_dir)
            logger.info("Disk Filter: Analyzing %s" % path)

            diff = None

            if not args.rerun and os.path.exists(os.path.join(path, 'disk_diff.txt')):
                diff = pickle.load(open(os.path.join(path, 'disk_diff.txt'), 'rb'))

            else:

                dcap_uri = os.path.join(path, "dcap")

                disk_analysis = DiskAnalysis(dcap_uri, args.machine_type, args.disk_img)
                diff = disk_analysis.run()

                pickle.dump(diff, open(os.path.join(path, 'disk_diff.txt'), 'wb'))

            if not diff:
                logger.error("Error processing disk analysis for %s . . . skipping!" % path)
                continue

            disk_filter.add_analysis(diff)

        # adjust filter
        if not args.noadjust:
            disk_filter.adjust_filter(9)

        # write filter to disk
        f = open(args.output_path+'.disk', 'w')
        f.write(pprint.pformat(disk_filter.occurrences_dict))
        f.close()


if __name__=="__main__":
    # parse args

    parser = argparse.ArgumentParser()
    
    parser.add_argument("-i", "--sample_id", action='store', dest='sample_id',
                        help="Creates filter from this sample")
    parser.add_argument("-u", "--db_host", action='store', dest='db_host',
                        default="lophi-dev",
                        help="Database host")
    parser.add_argument("--dir", action='store', dest='dir_path',
                        help="Input directory of analysis results")
    parser.add_argument("--type", action='store', type=int, dest='machine_type',
                        help="Machine type for dcap file 1 : Phys -> 0; KVM -> 2")
    parser.add_argument("--diskimg", action='store', dest='disk_img',
                        help="Local copy of base disk image for analysis")
    parser.add_argument("-r", action='store_true', dest='rerun', default=False,
                        help="Rerun all analyses.")
    parser.add_argument("--noadjust", action='store_true', dest='noadjust', default=False,
                        help="Toggle thresholding adjustment of filter")
    parser.add_argument("-o", action='store', dest='output_path',
                        help="Output path to save the filters, e.g. '-o filter' will give 'filter.disk' and 'filter.mem'")
    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    args = parser.parse_args()

    main(args)
