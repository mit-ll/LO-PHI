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

from lophi_analysis.analysis_filter import MemoryFilter
import lophi.globals as G
from memory_analysis import MemoryAnalysis


def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not args.output_path:
        logger.error("Please specify a filename to save the filters to.")
        sys.exit(0)

    import lophi_automation.database.datastore as datastore
    db_uri = 'mongodb://'+args.db_host+':27017/lophi_db'
    analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)
    results = analysis_datastore.db.collection.find({'status': 'COMPLETED',
                                                     "machine_type": args.machine_type,
                                                     "analysis_script": args.analysis_script,
                                                     "volatility_profile":
                                                         args.volatility_profile,
                                                     "sample":args.sample_id})

    logger.info("Creating filter from %d analyses..."%results.count())

    # Memory
    mem_filter = MemoryFilter()

    try:
        os.makedirs(args.output_path)
    except:
        pass

    for result in results:
        mem_results = result['memory_analysis']
        logger.info("Memory Filter: Analyzing %s" % result['_id'])

        diff = None

        if not args.rerun and os.path.exists(os.path.join(args.output_path,
                                                          result['_id'] + "_" +
                                                          'mem_diff.txt')):
            diff = pickle.load(open(os.path.join(args.output_path,
                                                 result['_id'] + "_" +
                                                 'mem_diff.txt'), 'rb'))

        else:

            diff = result['memory_analysis']

            pickle.dump(diff, open(os.path.join(args.output_path,
                                                result['_id'] + "_" +
                                                'mem_diff.txt'), 'wb+'))

        if not diff:
            logger.error("Error processing memory analysis for %s . . . skipping!" % result['_id'])
            continue

        mem_filter.add_analysis(diff)

    # adjust the filter
    mem_filter.adjust_filter(1)

    # write filter to disk
    # pprint.pprint(mem_filter.occurrences_dict)
    f = open(os.path.join(args.output_path, 'filter.mem'), 'w')
    f.write(pprint.pformat(mem_filter.occurrences_dict))
    f.close()




if __name__=="__main__":
    # parse args

    parser = argparse.ArgumentParser()
    

    parser.add_argument("-S", "--db_host", action='store', dest='db_host',
                        default="localhost",
                        help="Database host")

    parser.add_argument("-i", "--sample_id", action='store', dest='sample_id',
                        help="Creates filter from this sample")
    parser.add_argument("-a", action='store', dest='analysis_script',
                        help="Name of analysis that was run")
    parser.add_argument("-T", action='store', dest='machine_type', type=int,
                        help="Machine type for filter")
    parser.add_argument("-p", action='store', dest='volatility_profile',
                        help="Volatility profile")

    parser.add_argument("-o", action='store', dest='output_path',
                        help="Output path to save the filters, e.g. '-o filter' will give 'filter.disk' and 'filter.mem'")

    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    parser.add_argument("-r", action='store_true', dest='rerun', default=False,
                    help="Rerun all analyses.")

    args = parser.parse_args()

    main(args)
