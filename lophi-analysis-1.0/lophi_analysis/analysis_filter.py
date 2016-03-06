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
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)

# 3rd Party
import volatility.plugins.overlays.windows.tcpip_vtypes as tcpip_vtypes

class Filter(object):
    def __init__(self):
        self.occurrences_dict = {}
        self.num_analyses = 0

    def add_analysis(self, results_dict):
        logger.error("add_analysis() Should be overridden")

class DiskFilter(Filter):

    def __init__(self, filter_dict=None):
        super(DiskFilter, self).__init__()

        if filter_dict:
            self.occurrences_dict = filter_dict

    def add_analysis(self, results_dict):
        # (operation, filename, inode) -> counter
        for event in results_dict:
            self.occurrences_dict[event] = self.occurrences_dict.get(event, 0) + 1

        self.num_analyses += 1

    def adjust_filter(self, threshold):
        #logger.info("Adjusting filter. . .")
        print "Adjusting filter . . ."
        if threshold < 0 or threshold > self.num_analyses:
            # do nothing
            logger.info("Threshold of %d cannot be applied for %d analyses. Skipping adjustment." % (threshold, self.num_analyses))
            return

        events_to_remove = []
        for event, analyses_count in self.occurrences_dict.iteritems():
            if analyses_count < threshold:
                events_to_remove.append(event)

        for event in events_to_remove:
            del self.occurrences_dict[event]

        total = len(self.occurrences_dict.keys())

        if total == 0:
            print "Total events == 0, no adjustment needed."
        else:
            num_kept = total - len(events_to_remove)
            percentage = float(num_kept)/total
            threshold_percentage = float(threshold)/self.num_analyses
            stats = "Adjusted Disk Filter %d / %d events (%f) occurred in at least %f of trials" % (num_kept, total, percentage, threshold_percentage)

            print stats
            #logger.info(stats)

    def apply_filter(self, disk_results_dict, use_inodes=True):
        events_to_remove = []

        if use_inodes:
            for event in disk_results_dict.keys():
                if event in self.occurrences_dict:
                    del disk_results_dict[event]
        else:
            occurrences_dict_no_inodes = {}
            for k, v in self.occurrences_dict.iteritems():
                (op_type, filename, inode) = k
                occurrences_dict_no_inodes[(op_type, filename)] = v

            for event in disk_results_dict.keys():
                (op_type, filename, inode) = event
                if (op_type, filename) in occurrences_dict_no_inodes:
                    del disk_results_dict[event]

        return disk_results_dict

class MemoryFilter(Filter):

    def __init__(self, filter_dict=None):
        super(MemoryFilter, self).__init__()
        # plugin -> {'Added Entries':{'entry1':count, }, 'Removed Entries':{'entry1':count, }}

        self.SPECIAL_PLUGINS_KEY = {
            'filescan': self.get_filescan_key,
            'ldrmodules': self.get_ldrmodules_key,
            'psscan': self.get_psscan_key,
            'timers': self.get_timers_key,
            'envars': self.get_envars_key,
            'netscan': self.get_netscan_key,
            'psxview': self.get_psxview_key
            }

        if filter_dict:
            self.occurrences_dict = filter_dict



    # build up the filter
    def add_analysis(self, results_dict):
        # plugin -> {'Added Entries':[], 'Removed Entries':[]}
        for plugin in results_dict:

            if plugin not in self.occurrences_dict:
                self.occurrences_dict[plugin] = {}

            # skip if we got an error running this plugin
            if not isinstance(results_dict[plugin], dict):
                continue

            # some plugins need special treatment
            ret_dict = None
            if plugin in self.SPECIAL_PLUGINS_KEY:
                ret_dict = self.add_special_plugin(results_dict[plugin], plugin)
            else:
                ret_dict = results_dict[plugin]

            for category in ret_dict:
                if category not in self.occurrences_dict[plugin]:
                    self.occurrences_dict[plugin][category] = {}

                for entry in ret_dict[category]:
                    # sometimes entry is a non-hashable object like a list
                    # convert to a string for now
                    if isinstance(entry, list):
                        entry = ' '.join(entry)
                    self.occurrences_dict[plugin][category][entry] = \
                        self.occurrences_dict[plugin][category].get(entry, 0) + 1

        # increment the number of analyses we added
        self.num_analyses += 1


    # adjust the filter for special plugins
    def adjust_filter(self, threshold):
        #logger.info("Adjusting filter. . .")
        print "Adjusting filter. . ."

        if threshold < 0 or threshold > self.num_analyses:
            # do nothing
            return

        for plugin in self.occurrences_dict:
            if plugin in self.SPECIAL_PLUGINS_KEY:
                for category in self.occurrences_dict[plugin]:

                    adjusted_dict = {}
                    # {entry -> {count1 : num_of_runs, count2 : num_of_runs} }
                    # count up minimum number of occurrences that show up in runs
                    entry_dict = {}
                    for entry, analyses_count in self.occurrences_dict[plugin][category].iteritems():
                        (k, count) = entry

                        if k not in entry_dict:
                            entry_dict[k] = {}

                        for c in entry_dict[k]:
                            if count > c:
                                entry_dict[k][c] += analyses_count

                        entry_dict[k][count] = analyses_count

                    # now for each key, pick the highest count with the analyses_count that passes the threshold
                    for k in entry_dict:
                        highest_count = -1
                        analyses_count_for_highest_count = -1
                        for count, analyses_count in entry_dict[k].iteritems():
                            if analyses_count >= threshold and count > highest_count:
                                highest_count = count
                                analyses_count_for_highest_count = analyses_count

                        if highest_count > 0:
                            adjusted_dict[(k, highest_count)] = analyses_count_for_highest_count

                    total = len(self.occurrences_dict[plugin][category].keys())
                    print "Adjusted Memory Filter plugin %s: %s" % (plugin, category)
                    if total == 0:
                        print "  Total events == 0, no adjustment needed."
                    else:
                        num_kept = len(adjusted_dict.keys())
                        percentage = float(num_kept)/total
                        threshold_percentage = float(threshold)/self.num_analyses
                        stats = "  %d events (%f) occurred in at least %f of trials" % (num_kept, percentage, threshold_percentage)

                        # replace with adjusted dict
                        self.occurrences_dict[plugin][category] = adjusted_dict

                        print stats
                        #logger.info("Adjusted Memory Filter plugin %s" % (plugin))
                        #logger.info(stats)


    # apply filter
    def apply_filter(self, mem_results_dict):
        """
        Applies filter to this dictionary of memory analysis results
        :param mem_results_dict:
        :return:
        """
        for plugin in mem_results_dict:
            if plugin in self.occurrences_dict:

                # go through each category
                for category in mem_results_dict[plugin]:
                    if category in self.occurrences_dict[plugin]:

                        # Filtered list of entries
                        filtered_set = set(mem_results_dict[plugin][category])

                        # special treatment for some plugins
                        if plugin in self.SPECIAL_PLUGINS_KEY:
                            # {(key, count) -> number of runs this key showed up in}
                            # TODO should the filter match exactly?

                            for entry_filter in self.occurrences_dict[plugin][category]:
                                (k_filter, count_filter) = entry_filter

                                # check each entry in the results for this plugin category
                                # and see if the count matches up
                                count_results = 0
                                entries_to_remove = []
                                for entry in filtered_set:
                                    k_results = self.SPECIAL_PLUGINS_KEY[plugin](entry)
                                    if k_filter == k_results:
                                        count_results += 1
                                        entries_to_remove.append(entry)

                                # check if counts match up
                                # TODO here is a place where it matters whether the filter matches exactly
                                if count_filter >= count_results:
                                    # we have fewer or the exact number of entries that match the key
                                    # so we should remove all of the entries
                                    for entry in entries_to_remove:
                                        filtered_set.remove(entry)


                                # Otherwise, we have more entries than expected that match the key
                                # so we have to keep all of them b/c we don't know which ones
                                # to attribute to the binary that executed


                        else: # normal plugins

                            for entry in self.occurrences_dict[plugin][category]:
                                try:
                                    filtered_set.remove(entry)

                                except:
                                    pass

                        # the filtered_set replaces what was in the results dict
                        mem_results_dict[plugin][category] = list(filtered_set)

        return mem_results_dict


    # Try to remove fields in entries that can change across memory snapshots,
    # e.g. offsets
    def add_special_plugin(self, plugin_dict, plugin):
        ret_dict = {}
        for category in plugin_dict:
            tmp_dict = {}

            # tmp dict for multiple open file handles to same file
            for entry in plugin_dict[category]:

                k = self.SPECIAL_PLUGINS_KEY[plugin](entry)
                tmp_dict[k] = tmp_dict.get(k, 0) + 1

            ret_dict[category] = tmp_dict.items()

        return ret_dict


    def get_filescan_key(self, entry):

        # offset, ptr, hnd, access, name

        str1 = entry[:40]
        str2 = entry[40:]
        # (offset, ptr, hnd, access) = str1.split()
        name = str2.strip()

        return name


    def get_ldrmodules_key(self, entry):
        # pid, process, base, inload, ininit, inmem, mappedpath

        # (pid, process, base, inload, ininit, inmem, mappedpath) = entry.split()
        str1 = entry[:69]
        str2 = entry[69:]
        (pid, process, base, inload, ininit, inmem) = str1.split()
        mappedpath = str2.strip()

        return mappedpath


    def get_psscan_key(self, entry):
        # offset, name, pid, ppid, pdb, time_created, time_exited (may be missing)

        name = entry[19:33].strip()
        return name


    def get_timers_key(self, entry):
        # offset, duetime, period, signaled, routine, module

        (offset, duetime, period, signaled, routine, module) = entry.split()
        return module

    def get_envars_key(self, entry):

        #Pid      Process              Block        Variable           Value
        split_var = entry.split()

        return split_var[3], "".join(split_var[4:])

    def get_netscan_key(self, entry):

        #Offset(P)  Proto    Local Address                  Foreign Address      State            Pid      Owner          Created

        split_var = entry.split()

        proc = ""
        if len(split_var) > 5:
            proc = split_var[5]

        state = "N/A"
        if split_var[4] in tcpip_vtypes.TCP_STATE_ENUM.values():
            state = split_var[4]
        return split_var[1], split_var[2].split(":")[0], split_var[3].split(
            ":")[0], state

    def get_psxview_key(self, entry):

        # Offset(P)          Name                    PID pslist psscan thrdproc pspcid csrss session deskthrd
        str1 = entry[19:42].strip()
        str2 = entry[42:]
        split_var1 = str1.split()
        split_var2 = str2.split()

        if len(split_var1) == 0 or len(split_var2) == 0:
            return None
        if len(split_var2) < 7:
            return str1, "ERROR"
        return str1, split_var2[1], split_var2[2], split_var2[3], split_var2[
            4], split_var2[5], split_var2[6], split_var2[7]


def test():
    f = MemoryFilter()

    m = {'foo':{'Added Entries':[1,2,3], 'Removed Entries':[4,5,6]},
         'bar':{},
         'baz':{'Added Entries':[10,20,30], 'Removed Entries':[40,50,60]}}

    f.add_analysis(m)
    pprint.pprint(f.occurrences_dict)

    m = {'foo':{},
         'bar':{},
         'baz':{'Added Entries':[10,20], 'Removed Entries':[60]}}

    f.add_analysis(m)
    pprint.pprint(f.occurrences_dict)

    m = {'foo':{'Added Entries':[1,2,3], 'Removed Entries':[4,5,6]},
         'bar':{},
         'baz':{'Added Entries':[20], 'Removed Entries':[40,50]}}

    f.add_analysis(m)
    pprint.pprint(f.occurrences_dict)

