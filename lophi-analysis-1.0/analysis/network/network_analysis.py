# Native
import argparse
import binascii
import hashlib
import multiprocessing
import os
import pprint
import shutil
import tarfile
import tempfile
import time
import logging
logger = logging.getLogger(__name__)


# 3rd Party
import dpkt

# LO-PHI
import lophi.globals as G
import lophi_automation.database.datastore as datastore
from lophi.capture.network import PcapReader
import lophi_semanticgap.network as NET



##+===============================================================================
##
## Differential network analysis
##

class NetworkAnalysis(object):
    """
    Memory Differential Analysis object -- represents a differential memory analysis
    between a clean memory sample and a dirty memory sample
    """

    def __init__(self, dcap_filename):
        self.dcap_filename = dcap_filename

    ## run all of our analysis
    def run(self):

        reader = PcapReader(self.dcap_filename)

        (recognized,unknown) = NET.extract_tuples(reader)

        packets = []
        for pkt in recognized:
            port_desc = ""
            if pkt['protocol'] == "UDP" and pkt['port_dst'] in NET.UDP_PORTS:
                port_desc = NET.UDP_PORTS[pkt['port_dst']]
            if pkt['protocol'] == "TCP" and pkt['port_dst'] in NET.TCP_PORTS:
                port_desc = NET.TCP_PORTS[pkt['port_dst']]

            if port_desc != "":
                port_desc = "("+port_desc+")"

            dns_report = tuple(pkt.get('dns', []))
            val = (pkt['protocol'],
                                        pkt['ip_src'],
                                        pkt['port_src'],
                                        pkt['ip_dst'],
                                        pkt['port_dst'],
                                        port_desc,
                   dns_report)
            packets.append(val)

        return packets




def network_analyze_from_db(analysis_id, db_uri):
    """
    Pulls the memory samples from the database and then runs the analysis
    """

    try:
        analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)
        files_datastore = datastore.Datastore(db_uri+'/fs.files')

        analysis_doc = analysis_datastore.db.collection.find_one({'status':'COMPLETED',
                                                                  '_id': analysis_id})

        if not analysis_doc:
            logger.debug("No analysis found for %s" % analysis_id)
            return

        working_path = '/tmp/lophi-tmp-net'

        if not os.path.exists(working_path):
            os.mkdir(working_path)

        logger.info("Downloading network snapshots for analysis id %s" %
                    analysis_id)

        outdir_path = os.path.join(working_path, analysis_id)
        os.mkdir(outdir_path)

        # grab dcap
        net_capture_id = analysis_doc['output_files']['network_capture']

        dcap_local = os.path.join(outdir_path, 'net.dcap')

        logger.debug("Downloading DCAP to %s" % dcap_local)
        files_datastore.download_file(net_capture_id, dcap_local)


        # run the analysis
        logger.info("Running network analysis on %s" % analysis_id)
        net_analysis = NetworkAnalysis(dcap_local)

        ret = net_analysis.run()
        analysis_datastore.db.collection.update({'_id': analysis_id},
                                                {'$set': {'network_analysis':
                                                              ret}})

        # clean up
        logger.info("Cleaning up %s" % outdir_path)
        shutil.rmtree(outdir_path)

    except Exception as e:
        logger.error("Error doing network analysis for %s : %s" % (analysis_id,
                                                             str(e)))



def network_analyze_all(db_uri, rerun):

    analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)

    results = analysis_datastore.db.collection.find({'status':
                                                    'COMPLETED'}).batch_size(1)

    logger.info("Number of completed analyses: %d" % results.count())

    for analysis_doc in results:
        if "network_analysis" not in analysis_doc or rerun:
            network_analyze_from_db(analysis_doc['_id'], db_uri)


def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.run_all:
        logger.info("Running analysis on all completed samples in the database.")
        network_analyze_all('mongodb://'+args.db_host+':27017/lophi_db',
                           args.rerun)

if __name__ == "__main__":
    # parse args

    parser = argparse.ArgumentParser()

    parser.add_argument("-a", "--all", action='store_true', dest='run_all',
                        help="Run memory analysis on all completed samples in the database")
    parser.add_argument("-S", "--db_host", action='store', dest='db_host',
                        default="localhost",
                        help="Database host")
    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    parser.add_argument("-r", action='store_true', dest='rerun', default=False,
                    help="Rerun all analyses.")

    args = parser.parse_args()

    main(args)
