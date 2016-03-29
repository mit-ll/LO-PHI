#!/usr/bin/env python
"""
    Memory and Disk Noise Filter

    (c) 2015 Massachusetts Institute of Technology
"""


# Native
import argparse
import sys
import pprint
import logging
logger = logging.getLogger(__name__)

# LO-PHI

from lophi_analysis.analysis_filter import DiskFilter


def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not args.filter_path:
        logger.error("Please specify a file containing the disk filter to be applied.")
        sys.exit(0)

    # for now, process local file
    if args.analysis_path:
        logger.info("Analyzing local disk analysis file %s" % args.analysis_path)

        # open file
        f = open(args.analysis_path, 'r')
        results_string = f.read()
        f.close()

        # try to convert into a dict
        import ast
        results_dict = ast.literal_eval(results_string)

        # open the filter
        f = open(args.filter_path, 'r')
        filter_string = f.read()
        f.close()

        filter_dict = ast.literal_eval(filter_string)

        disk_filter = DiskFilter(filter_dict)

        logger.info("Read disk analysis containing %d lines" % len(results_dict.keys()))

        # apply the filter
        filtered_results_dict = disk_filter.apply_filter(results_dict, use_inodes=False)

        logger.info("Filtered disk analysis contains %d lines" % len(filtered_results_dict.keys()))

        pprint.pprint(filtered_results_dict)


if __name__=="__main__":
    # parse args

    parser = argparse.ArgumentParser()
    
    parser.add_argument("-i", "--sample_id", action='store', dest='sample_id',
                        help="Creates filter from this sample")
    parser.add_argument("-S", "--db_host", action='store', dest='db_host',
                        default="lophi-dev",
                        help="Database host")
    parser.add_argument("-a", action='store', dest='analysis_path',
                        help="Local file containing disk analysis")
    parser.add_argument("-f", action='store', dest='filter_path',
                        help="Local file containing disk filter")
    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    args = parser.parse_args()

    main(args)
