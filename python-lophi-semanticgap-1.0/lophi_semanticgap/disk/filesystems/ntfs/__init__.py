#!/usr/bin/env python
"""
     Adapted from analyzeMFT
"""
# Native
import sys
import os
import logging

# 3rd Party
from analyzemft import mft


SIAttributeSizeXP = 72
SIAttributeSizeNT = 48

logger = logging.getLogger(__name__)


class MftSession:
    '''Class to describe an entire MFT processing session'''

    def __init__(self, MFT_RAW):
        
        self.MFT_RAW = MFT_RAW
        
        self.mft = {}
        self.fullmft = {}
        self.folders = {}
        self.debug = False
        self.mftsize = 0



    def print_runs(self):
        for i in self.mft:
            record_num = i
            record = self.mft[i]
            filename = record['filename']
            
            if ('corrupt' in record and record['corrupt']) or ('baad' in record and record['baad']):
                print "Bad or corrupt record %d" %i
            
            output = str(record_num) + " " + filename
            
            resident_attribs = []
            
            for ATRrecord in record['attributes']:

                if ATRrecord['res'] != 0:
 
                    output += " " + str(mft.ATTRIBUTE_TYPE_TABLE[ATRrecord['type']]) + " " + str(ATRrecord['dataruns'])

                else:
                    resident_attribs.append(mft.ATTRIBUTE_TYPE_TABLE[ATRrecord['type']])
                    
                if ATRrecord['type'] == 0x20: # attribute list
                    output += '\n\t\tAttribute List: %s' % str(ATRrecord)

            output += '\n\t\tResident Attribs: %s' % str(resident_attribs)

            print output


    def print_problem_runs(self):
        for i in self.mft:
            record_num = i
            record = self.mft[i]
            filename = record['filename']
            datacnt = record['datacnt']
            
            data_attribute = None
            if datacnt > 0:
                data_attribute = record['data', datacnt-1]
            
            if data_attribute and 'dataruns' in data_attribute:
                for run in data_attribute['dataruns']:
                    (num_blocks, addr) = run
                    
                    # ceiling taken from 10GB/1024B  (block size)
                    if (num_blocks < 0 or num_blocks > 10485760 or addr < 0 or addr > num_blocks > 10485760):
                        print record_num, filename, datacnt, data_attribute        
        

    #Provides a very rudimentary check to see if it's possible to store the entire MFT in memory
    #Not foolproof by any means, but could stop you from wasting time on a doomed to failure run.
    def sizecheck(self):
          
        #The number of records in the MFT is the size of the MFT / 1024
        mftsize = long(os.path.getsize(self.mft_file)) / 1024
        
        logger.debug('There are %d records in the MFT' % mftsize)
        
        #The size of the full MFT is approximately the number of records * the avg record size
        #Avg record size was determined empirically using some test data
        sizeinbytes = mftsize * 4500
        
        logger.debug('Need %d bytes of memory to save into memory' % sizeinbytes)
        
        try:
            arr = []
            for i in range(0, sizeinbytes/10):
                    arr.append(1)
        
        except(MemoryError):
            logger.error('Error: Not enough memory to store MFT in memory. TODO: FIX this')
            sys.exit()

     
    def process_mft_file(self):
          
        #self.sizecheck()
                           
        # 1024 is valid for current version of Windows but should really get this value from somewhere


        num_records = len(self.MFT_RAW)/1024

        logger.debug("%d number of records" % num_records)

        for i in range(num_records):          

            self.update_record(i, raw_record=None)
            
#             if self.options.progress:
#                 if num_records % (self.mftsize/5) == 0 and num_records > 0:
#                     print 'Building Filepaths: {0:.0f}'.format(100.0*num_records/self.mftsize) + '%'

        logger.debug("Building filepaths")            

        self.gen_filepaths()


    def get_folder_path(self, seqnum):
        #print "Building Folder For Record Number (%d)" % seqnum
        
        if seqnum not in self.mft:
            return 'Orphan'
        
        # If we've already figured out the path name, just return it
        if (self.mft[seqnum]['filename']) != '':
            return self.mft[seqnum]['filename']
        
        try:
        #                if (self.mft[seqnum]['fn',0]['par_ref'] == 0) or (self.mft[seqnum]['fn',0]['par_ref'] == 5):  # There should be no seq number 0, not sure why I had that check in place.
            if (self.mft[seqnum]['par_ref'] == 5): # Seq number 5 is "/", root of the directory
                self.mft[seqnum]['filename'] = '/' + self.mft[seqnum]['name']
                return self.mft[seqnum]['filename']
        except:  # If there was an error getting the parent's sequence number, then there is no FN record
            self.mft[seqnum]['filename'] = 'NoFNRecord'
            return self.mft[seqnum]['filename']
        
        # Self referential parent sequence number. The filename becomes a NoFNRecord note
        if (self.mft[seqnum]['par_ref']) == seqnum:
            print "Error, self-referential, while trying to determine path for seqnum %s" % seqnum
            self.mft[seqnum]['filename'] = 'ORPHAN/' + self.mft[seqnum]['name']
            return self.mft[seqnum]['filename']
        
        # We're not at the top of the tree and we've not hit an error
        parentpath = self.get_folder_path((self.mft[seqnum]['par_ref']))
        self.mft[seqnum]['filename'] =  parentpath + '/' + self.mft[seqnum]['name']
        
        return self.mft[seqnum]['filename']


    def gen_filepaths(self):

        for i in self.mft:

  #            if filename starts with / or ORPHAN, we're done.
  #            else get filename of parent, add it to ours, and we're done.

            # If we've not already calculated the full path ....
            if (self.mft[i]['filename']) == '':
        
                if ( self.mft[i]['fncnt'] > 0 ):
                    self.get_folder_path(i)
                    # self.mft[i]['filename'] = self.mft[i]['filename'] + '/' + self.mft[i]['fn',self.mft[i]['fncnt']-1]['name']
                    # self.mft[i]['filename'] = self.mft[i]['filename'].replace('//','/')
                    if self.debug: print "Filename (with path): %s" % self.mft[i]['filename']
                else:
                    self.mft[i]['filename'] == 'NoFNRecord'




    def update_record(self, record_no, raw_record = None):
        """
            Update record when it changes (or to initialize)
        """

        # if new data is provided, use the new data as the raw record,
        # otherwise, reparse it from the internal self.MFT_RAW file 
        if raw_record:
            assert len(raw_record) == 1024
            self.MFT_RAW = self.MFT_RAW[:record_no*1024] + raw_record + self.MFT_RAW[(record_no+1)*1024:]

        raw_record = self.MFT_RAW[record_no*1024:(record_no+1)*1024]            

  
        record = mft.parse_record(raw_record, mft.set_default_options())

        # Update the filepaths?
        if record['fncnt'] == 1:
            record['par_ref'] = record['fn',0]['par_ref']
            record['name'] = record['fn',0]['name']
        if record['fncnt'] > 1:
            record['par_ref'] = record['fn',0]['par_ref']
            for j in (0, record['fncnt']-1):
                #print record['fn',i]
                if (record['fn', j]['nspace'] == 0x1 or record['fn', j]['nspace'] == 0x3):
                    record['name'] = record['fn', j]['name']
            if (record.get('name') == None):
                record['name'] = record['fn', record['fncnt']-1]['name']
    
    
        # add the record to the MFT
        self.mft[record_no] = record
    
        # process children records, if any
        # children records are stored in other records or on disk (non-resident)
        self._process_children(record_no)
    


        # Need to call gen_filepaths()
        self.gen_filepaths()
        


        
    def _process_children(self, record_no):
        """
            Process all the children records for the parent MFT record at record_no
            
            Children records are all attributes stored separately, e.g. in another MFT
            record or (if non-resident) in the filesystem
        """

                    
        # check if this MFT record has an attribute list
        record = self.mft[record_no]

                
        if 'attribute_list' in record:
            
            # check if resident elsewhere in MFT or non-resident (in the filesystem somewhere)
            if record['attribute_list']['res'] != 0: # non-resident
                # TODO pull from filesystem - remember to use volume offsets
                pass
                
            # go through each attribute list entry and pluck from other MFT entries
            for attr_list_record in record['attribute_list']['records']:
                    
                # skip if it's in the current record                        
                if attr_list_record['mft_record_no'] != record_no:
                        
                    # find the other record and look for the attribute we need
                    raw_other_record = self.MFT_RAW[attr_list_record['mft_record_no']*1024:(attr_list_record['mft_record_no']+1)*1024]
                    other_record = mft.parse_record(raw_other_record, mft.set_default_options())
                    
                    self.mft[attr_list_record['mft_record_no']] = other_record
                                       
                    for attribute in other_record['attributes']:
                        if attribute['type'] == attr_list_record['type'] and \
                        attribute['name'] == attr_list_record['name']:
                        
                            record['attributes'].append(attribute)


        # look at non-resident records

        # TODO read the raw record from the filesystem, parse it, and add it?


if __name__=="__main__":
    
    url = "/media/disk2/mft.raw"
    f = open(url, 'rb')
    session = MftSession(f.read())
    session.process_mft_file()
    session.print_runs()
    
