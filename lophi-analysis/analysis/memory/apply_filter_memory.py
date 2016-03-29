#!/usr/bin/env python

"""
    Memory and Disk Noise Filter

    (c) 2015 Massachusetts Institute of Technology
"""


# Native
import ast
import argparse
import sys
import pprint
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G
from lophi_analysis.analysis_filter import MemoryFilter


def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not args.filter_path:
        logger.error("Please specify a file containing the memory filter to be applied.")
        sys.exit(0)

    # open the filter
    f = open(args.filter_path, 'r')
    filter_string = f.read()
    f.close()

    filter_dict = ast.literal_eval(filter_string)

    mem_filter = MemoryFilter(filter_dict)




    import lophi_automation.database.datastore as datastore
    db_uri = 'mongodb://'+args.db_host+':27017/lophi_db'
    analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)
    results = analysis_datastore.db.collection.find({'status': 'COMPLETED',
                                                     "machine_type": args.machine_type,
                                                     "analysis_script": args.analysis_script,
                                                     "volatility_profile": args.volatility_profile})

    logger.info("Processing %d analyses..."%results.count())

    for result in results:
        mem_results = result['memory_analysis']

        filtered_results_dict = mem_filter.apply_filter(mem_results)

        analysis_datastore.db.collection.update({'_id': result['_id']},
                                                {'$set': {
                                                    'memory_analysis_filtered':
                                                        filtered_results_dict}})

        logger.info("Filtered results for %s"%result['_id'])






if __name__=="__main__":
    # parse args

    parser = argparse.ArgumentParser()
    
    parser.add_argument("-i", "--sample_id", action='store', dest='sample_id',
                        help="Creates filter from this sample")
    parser.add_argument("-S", "--db_host", action='store', dest='db_host',
                        default="localhost",
                        help="Database host")

    parser.add_argument("-a", action='store', dest='analysis_script',
                        help="Name of analysis that was run")
    parser.add_argument("-T", action='store', dest='machine_type', type=int,
                        help="Machine type for filter")
    parser.add_argument("-p", action='store', dest='volatility_profile',
                        help="Volatility profile")


    parser.add_argument("-f", action='store', dest='filter_path',
                        help="Local file containing memory filter")

    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    args = parser.parse_args()

    main(args)
