"""
    Simple program to resubmitted any incomplete analysis

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import multiprocessing
import time
import sys

# Pymongo
from pymongo import MongoClient

# LO-PHI
from lophi_automation.network.command import LophiCommand
import lophi_automation.ext_interface.rabbitmq as rabbitmq
import lophi.globals as G

def get_incomplete_analysis(options,positionals):
    """
        Resubmit all incomplete analyses
    """

    out_queue = multiprocessing.Queue()
    ctrl_producer = rabbitmq.LOPHI_RabbitMQ_Producer(options.services_host,
                                                     out_queue,
                                                     G.RabbitMQ.CTRL_IN)
    ctrl_producer.start()

    uri = 'mongodb://'+options.services_host+':27017/'

    print "* Connecting to %s..."%uri

    # Initialize our database connections
    client = MongoClient(uri)

    # Loop over all of our analyses.
    db = client.lophi_db

    # Get a list of all of our samples
    samples_db = db.samples

    analyses = db.analyses

    samples = []
    for sample_entry in samples_db.find():

        has_completed = False
        cmd = None
        for analysis in analyses.find({"sample": sample_entry[
            'sample']}):

            if analysis['status'] == "COMPLETED":
                has_completed = True
            else:
                if analysis['machine_type'] == "":
                    analysis['machine_type'] = options.machine_type

                cmd = LophiCommand(cmd=G.CTRL_CMD_START,
                               analysis=analysis['analysis_script'],
                               machine_type=analysis['machine_type'],
                               machine=None,
                               volatility_profile=analysis['volatility_profile'],
                               sample_doc_id=analysis['sample'],
                               submitter=G.get_username_local())

        if not has_completed and cmd is not None:
            print "* Re-submitting sample (%s)"%sample_entry['sample']
            out_queue.put(str(cmd))


    # for analysis in analyses.find():
    #
    #
    #     if analysis['status'] != "COMPLETED":
    #
    #         print "* Resubmitting %s (Status: %s)" % (analysis['_id'],
    #                                                  analysis['status'])
    #
    #         if analysis['machine_type'] == "":
    #             continue
    #
    #         # # Prepare a job to send to the machine, using the sample doc id
    #         # cmd = LophiCommand(cmd=G.CTRL_CMD_START,
    #         #                    analysis=analysis['analysis_script'],
    #         #                    machine_type=analysis['machine_type'],
    #         #                    machine=None,
    #         #                    volatility_profile=analysis['volatility_profile'],
    #         #                    sample_doc_id=analysis['sample'],
    #         #                    submitter=G.get_username_local())
    #         #
    #         # out_queue.put(str(cmd))

    time.sleep(5)
    out_queue.put(G.CTRL_CMD_KILL)
    ctrl_producer.stop()

if __name__ == "__main__":
    import optparse
    opts = optparse.OptionParser()

    # RabbitMQ (for LARIAT, LAMBDA)
    opts.add_option("-S", "--services_host", action="store", type="string",
                   dest="services_host", default='localhost',
                   help="Host for global services (MongoDB/RabbitMQ)")

    opts.add_option("-T", "--machine_type", action="store", type="int",
                   dest="machine_type", default=None,
                   help="Default machine type if one doesn't exist")

    (options, positionals) = opts.parse_args()

    if options.machine_type is None:
        print "ERROR: Please default a default machine type"
        opts.print_help()
        sys.exit(0)

    get_incomplete_analysis(options, positionals)
