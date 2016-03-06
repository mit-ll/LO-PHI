#!/usr/bin/env python

"""
    Memory Analysis using volatility

    (c) 2015 Massachusetts Institute of Technology
"""


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

# LO-PHI
import lophi.globals as G
import lophi_automation.database.utils as utils
import lophi_automation.database.documents as documents
import lophi_automation.database.datastore as datastore
from lophi_semanticgap.memory.volatility_extensions import VolatilityWrapper

# specifically for Win7
PLUGINS_TO_USE = [
    # 'filescan',
    'modscan',
    'psscan',
    'envars',
    'ssdt',
    'netscan',


    # Malware
    # 'malfind',
    # 'svcscan',
    'ldrmodules',
    # 'threads',
    'driverirp',
    # 'devicetree',
    'psxview',
    #
    # 'dlllist',
    # 'driverirp',
    # 'driverscan',
    # 'getsids'
]

# PLUGINS_TO_USE = [
#     # 'apihooks',
#     'atoms',
#     'atomscan',
#     # 'bioskbd',
#     'callbacks',
#     'clipboard',
#     'cmdscan',
#     'connections',
#     'connscan',
#     'consoles',
#     # 'crashinfo',
#     'deskscan',
#     'devicetree',
#     # 'dlldump',
#     'dlllist',
#     'driverirp',
#     'driverscan',
#     # 'dumpcerts',
#     # 'dumpfiles',
#     'envars',
#     'eventhooks',
#     # 'evtlogs',
#     'filescan',
#     'gahti',
#     'gditimers',
#     'gdt',
#     'getservicesids',
#     'getsids',
#     'handles',
#     # 'hashdump',
#     # 'hibinfo',
#     # 'hivedump',
#     'hivelist',
#     'hivescan',
#     # 'hpakextract',
#     # 'hpakinfo',
#     'idt',
#     # 'iehistory',
#     # 'imagecopy',
#     'imageinfo',
#     # 'impscan',
#     'kdbgscan',
#     # 'kpcrscan',  # Takes ~30 min to run!
#     'ldrmodules',
#     # 'linux_arp',
#     # 'linux_banner',
#     # 'linux_bash',
#     # 'linux_check_afinfo',
#     # 'linux_check_creds',
#     # 'linux_check_evt_arm',
#     # 'linux_check_fop',
#     # 'linux_check_idt',
#     # 'linux_check_modules',
#     # 'linux_check_syscall',
#     # 'linux_check_syscall_arm',
#     # 'linux_check_tty',
#     # 'linux_cpuinfo',
#     # 'linux_dentry_cache',
#     # 'linux_dmesg',
#     # 'linux_dump_map',
#     # 'linux_find_file',
#     # 'linux_ifconfig',
#     # 'linux_iomem',
#     # 'linux_keyboard_notifier',
#     # 'linux_lsmod',
#     # 'linux_lsof',
#     # 'linux_memmap',
#     # 'linux_moddump',
#     # 'linux_mount',
#     # 'linux_mount_cache',
#     # 'linux_netstat',
#     # 'linux_pidhashtable',
#     # 'linux_pkt_queues',
#     # 'linux_proc_maps',
#     # 'linux_psaux',
#     # 'linux_pslist',
#     # 'linux_pslist_cache',
#     # 'linux_pstree',
#     # 'linux_psxview',
#     # 'linux_route_cache',
#     # 'linux_sk_buff_cache',
#     # 'linux_slabinfo',
#     # 'linux_tmpfs',
#     # 'linux_vma_cache',
#     # 'linux_volshell',
#     # 'linux_yarascan',
#     # 'lsadump',
#     # 'mac_arp',
#     # 'mac_check_syscalls',
#     # 'mac_check_sysctl',
#     # 'mac_check_trap_table',
#     # 'mac_dead_procs',
#     # 'mac_dmesg',
#     # 'mac_dump_maps',
#     # 'mac_find_aslr_shift',
#     # 'mac_ifconfig',
#     # 'mac_ip_filters',
#     # 'mac_list_sessions',
#     # 'mac_list_zones',
#     # 'mac_lsmod',
#     # 'mac_lsof',
#     # 'mac_machine_info',
#     # 'mac_mount',
#     # 'mac_netstat',
#     # 'mac_notifiers',
#     # 'mac_pgrp_hash_table',
#     # 'mac_pid_hash_table',
#     # 'mac_print_boot_cmdline',
#     # 'mac_proc_maps',
#     # 'mac_psaux',
#     # 'mac_pslist',
#     # 'mac_pstree',
#     # 'mac_psxview',
#     # 'mac_route',
#     # 'mac_tasks',
#     # 'mac_trustedbsd',
#     # 'mac_version',
#     # 'mac_volshell',
#     # 'mac_yarascan',
#     # 'machoinfo',
#     'malfind',
#     'mbrparser',
#     # 'memdump',
#     # 'memmap',
#     'messagehooks',
#     # 'mftparser',  ## seems to return lots of data that may or may not be useful
#     # 'moddump',
#     'modscan',
#     'modules',
#     'mutantscan',
#     # 'netscan', ## doesn't support WinXPSP3x86
#     # 'patcher',
#     'printkey',
#     'privs',
#     # 'procexedump',
#     # 'procmemdump',
#     'pslist',
#     'psscan',
#     # 'pstree',
#     'psxview',
#     # 'raw2dmp',
#     # 'screenshot',
#     'sessions',
#     # 'shellbags',
#     'shimcache',
#     'sockets',
#     'sockscan',
#     'ssdt',
#     # 'strings',
#     'svcscan',
#     'symlinkscan',
#     'thrdscan',
#     'threads',
#     # 'timeliner',
#     'timers',
#     'unloadedmodules',
#     'userassist',
#     'userhandles',
#     # 'vaddump',
#     'vadinfo',
#     # 'vadtree',
#     'vadwalk',
#     # 'vboxinfo',
#     # 'vmwareinfo',
#     # 'volshell',
#     # 'windows',
#     'wintree',
#     'wndscan',
#     # 'yarascan'
# ]

############################################################################
#
# Dictionary diffing
#
class DictDiff(object):
    """
    Determine difference between two dictionaries
    (1) entries added
    (2) entries removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, dict1, dict2):
        self.dict1 = dict1
        self.dict2 = dict2

        self.set1 = set(self.dict1.keys())
        self.set2 = set(self.dict2.keys())

        self.intersection = self.set1.intersection(self.set2)

    def added(self):
        return self.set2 - self.intersection

    def removed(self):
        return self.set1 - self.intersection

    def changed_keys(self):
        # TODO recurse on nested dicts?
        return set(k for k in self.intersection if self.dict2[k] != self.dict1[k])

    def unchanged_keys(self):
        return set(k for k in self.intersection if self.dict2[k] == self.dict1[k])




##+===============================================================================
##
## Differential memory analysis
##

class MemoryAnalysis(object):
    """
    Memory Differential Analysis object -- represents a differential memory analysis
    between a clean memory sample and a dirty memory sample
    """

    def __init__(self, clean_url, dirty_url, profile, memory_size=1073741824):
        self.clean_url = 'file://'+clean_url
        self.dirty_url = 'file://'+dirty_url
        self.profile = profile
        self.memory_size = memory_size


    ## run all of our analysis
    def run(self):

        clean_queue = multiprocessing.Queue()
        dirty_queue = multiprocessing.Queue()
        clean_p = multiprocessing.Process(target=self.analyze_sample, args=(self.clean_url, self.profile, clean_queue))
        dirty_p = multiprocessing.Process(target=self.analyze_sample, args=(self.dirty_url, self.profile, dirty_queue))

        clean_p.start()
        dirty_p.start()

        # get output
        clean_output = clean_queue.get()
        dirty_output = dirty_queue.get()

        clean_queue.close()
        dirty_queue.close()

        # TODO add a timeout and check for deadlock?
        clean_p.terminate()
        dirty_p.terminate()
        clean_p.join()
        dirty_p.join()


        return self.diff_volatility_output(clean_output, dirty_output)



    ##+===============================================================================
    ## Running volatility plugins
    ##

    ## Runs volatility plugins on a memory dump
    def analyze_sample(self, url, profile, output_queue, memory_size=1073741824):
        """
            Analyzes a single memory image sample
            Puts output in output queue
        """

        worker_id = multiprocessing.current_process().name
        logger.info(worker_id+" Running memory analysis for profile %s" % profile)

        t0 = time.time()
        vol_wrapper = VolatilityWrapper(url, profile, memory_size=memory_size)

        # return structure
        ret = {}

        for plugin_name in PLUGINS_TO_USE:

            try:
                logger.info("Running plugin: %s" % plugin_name)

                t1 = time.time()
                output = vol_wrapper.execute_plugin(plugin_name)

                t2 = time.time()

                # add to return structure
                ret[plugin_name] = output

                logger.info(worker_id+" ran plugin %s -- %d s." % (plugin_name, t2-t1))

            except Exception as e:
                logger.error(worker_id+" Error running plugin %s for memory image %s: %s" % (plugin_name, url, str(e)))


        logger.info(worker_id+" Putting result in output queue")
        output_queue.put(ret)

        tf = time.time()
        logger.info(worker_id+" Memory analysis completed in %d seconds" % (tf-t0))




    ## Diffs output of volatility plugins
    def diff_volatility_output(self, output_dict1, output_dict2):
        """
            Diffs output of volatility plugins
        """

        worker_id = multiprocessing.current_process().name
        logger.info(worker_id+" Diffing volatility output")

        # return structure
        ret = {}

        for plugin_name in output_dict1:

            output = {}

            try:

                if plugin_name not in output_dict2:
                    ret[plugin_name] = "Error: Dirty memory image did not have analysis for plugin %s" % plugin_name
                    continue


                output1 = output_dict1[plugin_name]
                output2 = output_dict2[plugin_name]


                if output1 and output2:

                    # check for a complete match
                    if output1 == output2:
                        output = {}  # No difference

                    else:

                        header = ""
                        # check output is dict vs text
                        if isinstance(output1, dict) or isinstance(output2, dict):

                            # sometimes VolatilityWrapper will output dicts
                            # data is stored under the 'DATA' key
                            # header may be under 'HEADER' key
                            header = output1.get('HEADER', "")

                            output1 = output1['DATA']
                            output2 = output2['DATA']

                            # tuples are hashable, lists are not (can't be used in sets)
                            output1 = map(lambda x: tuple(x) if isinstance(x,list) else x, output1)
                            output2 = map(lambda x: tuple(x) if isinstance(x,list) else x, output2)


                            # dict_diff = DictDiff(output1, output2)
                            # output['Removed Entries'] = dict_diff.removed()
                            # output['Added Entries'] = dict_diff.added()
                            # output['Changed Entries'] = {}
                            # for k in dict_diff.changed_keys():
                            #     output['Changed Entries'][k] = {'old':output1[k],
                            #                                     'new':output2[k]}

                        else:
                            output1 = output1.splitlines()
                            output2 = output2.splitlines()

                            header = output1[0]

                        output_set1 = set(output1)
                        output_set2 = set(output2)

                        intersect = output_set1.intersection(output_set2)

                        # want to preserve the order of the output
                        output['Removed Entries'] = [line for line in output1 if line in (output_set1 - intersect)]
                        output['Added Entries'] = [line for line in output2 if line in (output_set2 - intersect)]

                        # try to put a useful header at the beginning?
                        #output['Removed Entries'].insert(0, header)
                        #output['Added Entries'].insert(0, header)

                else:
                    output = "Error running this plugin on one or both memory images."

            except:
                logger.error(worker_id+" Error processing output for plugin %s" % plugin_name)
                output = "Error processing output for this plugin on one or both memory images."

            # add to return structure
            ret[plugin_name] = output

        return ret



def memory_analyze_from_db(analysis_id, db_uri):
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

        working_path = '/tmp/lophi-tmp-mem'

        if not os.path.exists(working_path):
            os.mkdir(working_path)

        logger.info("Downloading memory snapshots for analysis id %s" % analysis_id)

        outdir_path = os.path.join(working_path, analysis_id)
        os.mkdir(outdir_path)

        # grab memory snapshots
        clean_memory_dump_id = analysis_doc['output_files']['memory_dump_clean']
        dirty_memory_dump_id = analysis_doc['output_files']['memory_dump_dirty']

        clean_url = os.path.join(outdir_path, 'clean_mem')
        dirty_url = os.path.join(outdir_path, 'dirty_mem')

        logger.debug("Downloading clean memory dump to %s" % clean_url)
        files_datastore.download_file(clean_memory_dump_id, clean_url)

        logger.debug("Downloading dirty memory dump to %s" % dirty_url)
        files_datastore.download_file(dirty_memory_dump_id, dirty_url)

        clean_path_out = os.path.join(outdir_path, "sut_memory_clean.mfd")
        # unpack memory snapshots
        if tarfile.is_tarfile(clean_url):
            logger.debug("Unpacking %s" % clean_url)

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

        dirty_path_out = os.path.join(outdir_path, "sut_memory_dirty.mfd")
        if tarfile.is_tarfile(dirty_url):
            logger.debug("Unpacking %s" % dirty_url)

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

        # run the analysis
        logger.info("Running memory analysis on %s" % analysis_id)
        memory_analysis = MemoryAnalysis(clean_path_out, dirty_path_out, analysis_doc['volatility_profile'])

        ret = memory_analysis.run()
        analysis_datastore.db.collection.update({'_id': analysis_id},
                                                {'$set': {'memory_analysis': ret}})

        # clean up
        logger.info("Cleaning up %s" % outdir_path)
        shutil.rmtree(outdir_path)
    
    except Exception as e:
        logger.error("Error doing memory analysis for %s : %s" % (analysis_id, str(e)))



def memory_analyze_all(db_uri, rerun):


    analysis_datastore = datastore.Datastore(db_uri+G.DB_ANALYSES)

    results = analysis_datastore.db.collection.find({'status': 'COMPLETED'}).batch_size(1)

    logger.info("Number of completed analyses: %d" % results.count())

    for analysis_doc in results:
        if "memory_analysis" not in analysis_doc or rerun:
            memory_analyze_from_db(analysis_doc['_id'], db_uri)



def main(args):

    logging.basicConfig()

    # debug
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # check if files specified
    if (args.clean_disk_uri and
        args.dirty_disk_uri and
        args.profile):

        logger.info("Analyzing locally stored memory samples %s and %s" % (args.clean_disk_uri, args.dirty_disk_uri))
        memory_analysis = MemoryAnalysis(args.clean_disk_uri, args.dirty_disk_uri, args.profile)
        diff = memory_analysis.run()

        pprint.pprint(diff)

    # get id
    elif args.analysis_id:
        memory_analyze_from_db(args.analysis_id, 'mongodb://'+args.db_host+':27017/lophi_db')

    elif args.run_all:
        logger.info("Running analysis on all completed samples in the database.")
        memory_analyze_all('mongodb://'+args.db_host+':27017/lophi_db',
                           args.rerun)

    else:
        logger.error("Invalid arguments. Specify two local memory captures and a profile or an analysis ID in the database.")


if __name__ == "__main__":
    # parse args

    parser = argparse.ArgumentParser()
    
    parser.add_argument("-i", "--id", action='store', dest='analysis_id',
                        help="Runs memory analysis on a sample that we ran whose memory dumps and disk logs are in the database")
    parser.add_argument("-a", "--all", action='store_true', dest='run_all',
                        help="Run memory analysis on all completed samples in the database")
    parser.add_argument("--clean", action='store', dest='clean_disk_uri',
                        help="Local copy of clean memory capture to analyze")
    parser.add_argument("--dirty", action='store', dest='dirty_disk_uri',
                        help="Local copy of dirty memory capture to analyze")
    parser.add_argument("--profile", action='store', dest='profile',
                        help="Profile of local memory captures")
    parser.add_argument("-S", "--db_host", action='store', dest='db_host',
                        default="localhost",
                        help="Database host")
    parser.add_argument("-d", "--debug", action='store_true', dest='debug',
                        help="Debug output")

    parser.add_argument("-r", action='store_true', dest='rerun', default=False,
                    help="Rerun all analyses.")

    args = parser.parse_args()

    main(args)
