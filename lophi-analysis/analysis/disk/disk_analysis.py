"""
    Script to diff two sata logs

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import argparse
import hashlib
import multiprocessing
import os
import pprint
import shutil
import subprocess
import tempfile
import logging
logger = logging.getLogger(__name__)


# LO-PHI
import lophi.globals as G
from lophi.capture import CaptureReader
from lophi.data import DiskSensorPacket
from lophi_semanticgap.disk.sata import SATAInterpreter
from lophi_semanticgap.disk.sata_reconstructor import SATAReconstructor
from lophi_semanticgap.disk.filesystems import SemanticEngineDisk
# DB
import lophi_automation.database.datastore as datastore


##+===============================================================================
##
## Differential disk analysis
##
class DiskAnalysis(object):
    """
    This class takes a dcap file and builds a dictionary of the filesystem activity
    so that we can compare that dictionary against another dcap file.

    E.g. we can build a filesystem activity dictionary for VM and for Physical
    machines and compare the two
    """

    def __init__(self, dcap_url, machine_type, disk_image_url, output_dir):
        """
        :param dcap_url: path to DCAP file
        :param machine_type: machine type
        :param disk_image_url: path to base disk image
        """

        self.dcap_url = dcap_url
        self.machine_type = machine_type
        self.disk_img = disk_image_url

        # working dir
        self.output_dir = output_dir


    def run(self):
        # replay SATA
        disk_dict = self.replay()

        # clean up
        logger.debug("* Cleaning up %s" % self.output_dir)
        shutil.rmtree(self.output_dir)

        return disk_dict


    def replay(self):
        """
        Replays the raw log of SATA frames (captured as LOPHIPackets),
        bridges the semantic gap and returns human-readable text form
        """

        # copy our disk image to a temporary working image
        self.working_disk_img = os.path.join(self.output_dir, "disk.img.tmp")
        logger.debug("* Creating temporary working image from disk scan. (%s)" % self.working_disk_img)

        # Delete, copy, chmod new file

        try:
            os.unlink(self.working_disk_img)
        except OSError:
            pass
        
        cmd = "cp --sparse=always %s %s" % (self.disk_img, self.working_disk_img)
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        os.chmod(self.working_disk_img, 0755)
        
        # Set up our semantic bridge
        logger.debug("* Parsing disk image %s into our semantic engine... (This may take a while)" % self.working_disk_img)
        semantic_engine = SemanticEngineDisk(self.working_disk_img)

        # Start processing our dcap
        logger.debug("* Processing dcap file %s..." % self.dcap_url)
        # SATA Interpreter
        sata = SATAInterpreter()
        """
            @TODO Extract sector size from PyTSK
        """
        sata_reconstructor = SATAReconstructor(sector_size=G.SENSOR_DISK.DEFAULT_SECTOR_SIZE)

        # read from the cap file
        reader = CaptureReader(self.dcap_url)

        # output
        output_log = []

        # Loop over all of the dcap contents
        for (timestamp, data) in reader:

            disk_sensor_pkts = None

            if self.machine_type == G.MACHINE_TYPES.PHYSICAL:
                lophi_packet = type('AnonClass', (object,), { "sata_header": None, "sata_data": None })
                (lophi_packet.sata_header, lophi_packet.sata_data) = sata.extract_sata_data(data)

                if (lophi_packet.sata_header == None or
                    lophi_packet.sata_data == None):
                    logger.warning("Skipping abnormal physical SATA capture packet -- either sata header and/or data is None.")
                    continue

                # deal with SATA NCQ reordering
                disk_sensor_pkts = sata_reconstructor.process_packet(lophi_packet)
            else:
                # logger.debug(DiskSensorPacket(data))
                disk_sensor_pkts = [DiskSensorPacket(data)]

            # Process all of our disk packets
            if disk_sensor_pkts:
                for dsp in disk_sensor_pkts:
                    # Skip empty packets
                    if not dsp:
                        continue

                    try:
                        fs_operations = semantic_engine.get_access(dsp.sector,
                                                                   dsp.num_sectors,
                                                                   dsp.disk_operation,
                                                                   dsp.data)
                        if fs_operations == None:
                            logger.error("Got an operation to sector %s that is outside our disk." % dsp.sector)
                            continue

                        for op in fs_operations:
                            output_log.append(op)

                    except:
                        logging.exception("Encountered error while trying to bridge semantic gap for this disk access.")

        # return value
        fs_dict = {}

        # Consolidate filesystem activity into a set
        # fields should be 'sector', 'op', 'op_type', 'inode', 'filename', 'raw_data', 'semantic_data'
        # try to insert (operation, filename, inode)
        # for duplicates, use a counter
        for fs_operation in output_log:

            sector = fs_operation['sector']
            operation = fs_operation['op']
            operation_type = fs_operation['op_type']
            inode = fs_operation['inode']
            filename = fs_operation['filename']
            raw_data = fs_operation['raw_data']

            ## TODO - look at filesystem stuff for now -- more low level data later?
            # key = (sector, op, raw_data)
            key = (operation_type, filename, inode)

            if key in fs_dict:
                fs_dict[key] += 1
            else:
                fs_dict[key] = 1

        return fs_dict


    @staticmethod
    def fs_activity_diff(fs_dict1, fs_dict2):
        """
        Diffs two different filesystem activity dicts (created by replay())
        """

        # disk operations from first log that were not in second log
        diffkeys_in_1_not_2 = fs_dict1.viewkeys() - fs_dict2.viewkeys()
        diffkeys_in_2_not_1 = fs_dict2.viewkeys() - fs_dict1.viewkeys()

        diff_dict1_not_in_2 = dict((k, fs_dict1[k]) for k in diffkeys_in_1_not_2)
        diff_dict2_not_in_1 = dict((k, fs_dict2[k]) for k in diffkeys_in_2_not_1)

        return diff_dict1_not_in_2, diff_dict2_not_in_1




############################################################################
#
# Interacting with disk captures in database
#
############################################################################
def disk_analyze_all(db_uri, disk_img, machine_type):
    """
        Run disk analysis on all completed analyses
    """
    analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)

    results = analysis_datastore.db.collection.find({'status':'COMPLETED',
                                                     'machine_type':machine_type
                                                     }).batch_size(1)

    logger.info("Number of completed analyses: %d" % results.count())

    for analysis_doc in results:
        disk_analyze_from_db(analysis_doc['_id'], db_uri, disk_img)



def disk_analyze_from_db(analysis_id, db_uri, disk_img):
    """
        Reconstructs semantic information for a single disk capture log and
        inserts it into the database
        
        This does NOT compare disk captures from separate analyses.  That is
        for disk_analyze_single_comparison()
    """

    try:
        analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)
        files_datastore = datastore.Datastore(db_uri+'/fs.files')

        analysis_doc = analysis_datastore.db.collection.find_one({'status':'COMPLETED',
                                                                  "_id": analysis_id})

        if not analysis_doc:
            logger.debug("No analysis found for %s" % analysis_id)
            return

        working_path = '/tmp/lophi-tmp-disk'

        if not os.path.exists(working_path):
            os.mkdir(working_path)

        logger.info("Downloading dcap for analysis id %s" % analysis_id)

        outdir_path = os.path.join(working_path, analysis_id)
        os.mkdir(outdir_path)

        # grab the disk log
        disk_cap_id = analysis_doc['output_files']['disk_capture']
        disk_cap_url = os.path.join(outdir_path, 'dcap')

        logger.debug("Downloading disk capture log %s" % disk_cap_url)
        files_datastore.download_file(disk_cap_id, disk_cap_url)

        disk_analysis = DiskAnalysis(disk_cap_url, analysis_doc[
            "machine_type"], disk_img, outdir_path)
        result_dict = disk_analysis.run()

        # MongoDB doesn't like '.' in its dictionary keys, so we have to convert to a list
        ret = list(result_dict.iteritems())

        analysis_datastore.db.collection.update({'_id': analysis_id},
                                                {'$set': {'disk_analysis': ret}})

        # clean up
        logger.info("Cleaning up %s" % outdir_path)
        shutil.rmtree(outdir_path)

    except Exception as e:
        logger.error("Error doing disk analysis for %s: %s" % (analysis_id, str(e)))




############################################################################
#
# Main
#
############################################################################

def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # logger.debug("%s, %s, %d, %d, %s, %s" % (args.dcap_url1, args.dcap_url2, args.machine_type1, args.machine_type2, args.disk_img1, args.disk_img2))

    # check if files specified
    if (args.dcap_url and
        (args.machine_type != None) and
        args.disk_img):

        logger.info("Analyzing locally stored dcap file %s" % args.dcap_url)
        fs_dict = DiskAnalysis(args.dcap_url, args.machine_type, args.disk_img).run()

        pprint.pprint(fs_dict)


    # get id
    elif args.analysis_id:
        disk_analyze_from_db(args.analysis_id, 'mongodb://'+args.db_host+':27017/lophi_db', args.disk_img)


    # all
    elif args.run_all:
        logger.info("Running analysis on all completed samples in the database.")
        disk_analyze_all('mongodb://'+args.db_host+':27017/lophi_db',
                         args.disk_img, args.machine_type)

    else:
        logger.error("Invalid arguments. Specify a local dcap file or an analysis ID " +
                     "in the database and the path to a local copy of the base disk image.")

if __name__=="__main__":
    # parse args

    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--id", action='store', dest='analysis_id',
                        help="Runs disk analysis on a sample that we ran whose memory dumps and disk logs are in the database")
    parser.add_argument("-a", "--all", action='store_true', dest='run_all',
                        help="Run disk analysis on all completed samples in the database")
    parser.add_argument("--dcap", action='store', dest='dcap_url',
                        help="Local copy of dcap file to analyze")
    parser.add_argument("-T", "--type", action='store', type=int,
                                 dest='machine_type',
                        help="Machine type for dcap file 1 : Phys -> 0; KVM -> 2")
    parser.add_argument("--diskimg", action='store', dest='disk_img',
                        help="Local copy of base disk image for analysis")
    parser.add_argument("-u", "--db_host", action='store', dest='db_host',
                        default="lophi-dev",
                        help="Database host")
    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    args = parser.parse_args()

    main(args)


