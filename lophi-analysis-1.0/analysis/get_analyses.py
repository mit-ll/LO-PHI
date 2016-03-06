#!/usr/bin/env python

"""
    Memory Analysis using volatility

    (c) 2015 Massachusetts Institute of Technology
"""


# Native
import argparse
import os
import shutil
import tarfile
import logging
import sys

logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G
import lophi_automation.database.datastore as datastore
from lophi_automation.database.mongodb_al import MongoDb



def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    db_uri = 'mongodb://'+args.db_host+':27017/lophi_db'
    DB = MongoDb(db_uri)
    analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)
    files_datastore = datastore.Datastore(db_uri+'/fs.files')

    results = analysis_datastore.db.collection.find({'status':'COMPLETED',
                                                     "sample":args.sample_id,
                                                     'machine_type':int(args.machine_type)})

    logger.info("Number of completed analyses for sample id %s : %d" % (args.sample_id, results.count()))

    if not os.path.exists(args.out_dir):
        os.mkdir(args.out_dir)

    for analysis_doc in results:
        analysis_id = analysis_doc['_id']
        logger.info("Downloading files for analysis id %s" % analysis_id)

        outdir_path = os.path.join(args.out_dir, analysis_id)
        if not os.path.exists(outdir_path):
            os.mkdir(outdir_path)
        else:
            logger.info("Analysis directory already exists, skipping.")
            continue

        # write the analysis doc
        analysis_doc_f = open(os.path.join(outdir_path, 'analysis_doc'), 'w')
        analysis_doc_f.write(str(analysis_doc))
        analysis_doc_f.close()

        # grab the disk log
        disk_cap_id = analysis_doc['output_files']['disk_capture']
        disk_cap_url = os.path.join(outdir_path, 'disk.dcap')

        logger.debug("Downloading disk capture log %s" % disk_cap_url)
        files_datastore.download_file(disk_cap_id, disk_cap_url)

        # grab memory snapshots
        clean_memory_dump_id = analysis_doc['output_files']['memory_dump_clean']
        dirty_memory_dump_id = analysis_doc['output_files']['memory_dump_dirty']

        clean_url = os.path.join(outdir_path, 'clean_mem')
        dirty_url = os.path.join(outdir_path, 'dirty_mem')

        logger.debug("Downloading clean memory dump to %s" % clean_url)
        files_datastore.download_file(clean_memory_dump_id, clean_url)

        logger.debug("Downloading dirty memory dump to %s" % dirty_url)
        files_datastore.download_file(dirty_memory_dump_id, dirty_url)

        screenshot1 = os.path.join(outdir_path, 'screenshot_interm')
        screenshot1_id = analysis_doc['output_files']['screenshot']
        screenshot2 = os.path.join(outdir_path, 'screenshot_final')
        screenshot2_id = analysis_doc['output_files']['screenshot_final']

        if args.machine_type == 2:
            DB.download_file(screenshot1_id, screenshot1+'.ppm')
            DB.download_file(screenshot2_id,
            screenshot2+'.ppm')
        else:
            DB.download_file(screenshot1_id,
                                     screenshot1+'.png')
            DB.download_file(screenshot2_id,
            screenshot2+'.png')

        # unpack memory snapshots
        if tarfile.is_tarfile(clean_url):
            logger.debug("Unpacking %s" % clean_url)
            clean_path_out = os.path.join(outdir_path, "sut_memory_clean.mfd")
            clean_tar = tarfile.open(clean_url)
            clean_tar.extractall(outdir_path)
            clean_tar.close()

            # find stupid path
            p = os.path.join(outdir_path, 'lophi', 'tmp')
            p = os.path.join(p, os.listdir(p)[0])
            p = os.path.join(p, os.listdir(p)[0])

            logger.debug("Moving %s to %s" % (p, clean_path_out))
            shutil.move(p, clean_path_out)
            p = os.path.join(outdir_path, 'lophi')
            shutil.rmtree(p)

        if tarfile.is_tarfile(dirty_url):
            logger.debug("Unpacking %s" % dirty_url)
            dirty_path_out = os.path.join(outdir_path, "sut_memory_dirty.mfd")
            dirty_tar = tarfile.open(dirty_url)
            dirty_tar.extractall(outdir_path)
            dirty_tar.close()

            # find stupid path
            p = os.path.join(outdir_path, 'lophi', 'tmp')
            p = os.path.join(p, os.listdir(p)[0])
            p = os.path.join(p, os.listdir(p)[0])

            logger.debug("Moving %s to %s" % (p, dirty_path_out))
            shutil.move(p, dirty_path_out)
            p = os.path.join(outdir_path, 'lophi')
            shutil.rmtree(p)



if __name__=="__main__":
    # parse args

    parser = argparse.ArgumentParser()
    
    parser.add_argument("-i", "--id", action='store', dest='sample_id',
                        help="Get all completed analyses for this sample_id, e.g. 'sample_94f7757a2487b7bebb9cc0d4547c82ad'")
    parser.add_argument("-T", "--type", action='store', dest='machine_type',
                        type=int,
                        help="Type of analysis - Physical 0, KVM 2",
                        default=None)
    parser.add_argument("-u", "--db_host", action='store', dest='db_host',
                        default="localhost",
                        help="Database host")
    parser.add_argument("-o", "--out_dir", action='store', dest='out_dir',
                        help="Output directory")
    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    args = parser.parse_args()

    if args.machine_type is None:
        logger.error("Please provide a machine type.")
        parser.print_help()
        sys.exit(0)

    main(args)
