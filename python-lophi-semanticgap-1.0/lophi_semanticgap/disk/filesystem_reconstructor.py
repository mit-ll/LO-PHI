import logging
import struct

logger = logging.getLogger(__name__)
from lophi_semanticgap.disk.filesystems.ntfs import *
# LOPHI
import lophi.globals as G

#### ADDING FORENSIC ANALYSIS CODE ####
# 3rd Party
import pytsk3


logger = logging.getLogger("FS")
logger.propagate = False
hdlr = logging.FileHandler('/tmp/IceBlock-TSK.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

MFT_ENTRY_SIZE = 1024 # Bytes
class Write_Img_Info(pytsk3.Img_Info):
    """
    Creates an updateable Img_Info that pushes changes to disk.
    """
    def __init__(self, url, sector_size):
        self.URL = url
        self.SECTOR_SIZE = sector_size
        
        ## Open the image
        self.fd = open(url, 'r+b')
        if not self.fd:
            raise IOError("Unable to open %s" % url)

        ## Call the base class with an empty URL
        pytsk3.Img_Info.__init__(self, '')

    def get_size(self):
        """ This function returns the size of the image """
        return os.path.getsize(self.URL)

    def read(self, off, length):
        """
        This returns byte ranges from the image, using the image
        """
        
        self.fd.seek(off)
        return self.fd.read(length)
        
    def write(self, sector, sector_count, data):
        """ Writes data to the img """
        
        off = sector*self.SECTOR_SIZE
        self.fd.seek(off)
        self.fd.write(data)


    def close(self):
        """ This is called when we want to close the image """
        self.fd.close()


class SemanticEngineDisk:
    
    """
        Base class for representing a disk containing SemanticEngineVolumes
    """

    
    def __init__(self,url):
        # parse out the different volumes
        logger.info("Initializing Semantic Engine")    
        self.url = url
        self.img = pytsk3.Img_Info(url=self.url)
        self.VOL_INFO = pytsk3.Volume_Info(self.img)

        self.vol_to_se = {}
        self.VOLUMES = []
        self.VOLUME_BOUNDARIES = []

        # print out some info about the disk image
        '''
        print("--- Volume info ---")
        print("Current: %d" % self.VOL_INFO.current)
        print("VS Type: %d" % self.VOL_INFO.info.vstype)
        print("Offset: %d" % self.VOL_INFO.info.offset)
        print("Block Size: %d" % self.VOL_INFO.info.block_size)
        print("Endian: %d" % self.VOL_INFO.info.endian)
        print("Partition List: %s" % self.VOL_INFO.info.part_list)
        print("Parition Count: %d" % self.VOL_INFO.info.part_count)
        print("--- Volume info ---")
        '''
        # Add each volume
        for vol in self.VOL_INFO:
            self.add_volume(vol)

                
    def add_volume(self, vol):
        """
            Add a new volume
            
            WARNING: These must be added in sequential order!
        """
        #print("--- Partition ---")
        #print("Start: %d" % vol.start)
        #print("Length: %d" % vol.len)
        #print("Description: %s" % vol.desc)
        #print("Address: %d" % vol.addr)
        #print("Flags: %d" % vol.flags)

        logger.info("Adding new volume: %s" % vol.desc) 
        type = vol.desc.split(" ")[0]
        self.VOLUMES.append(vol)
            
        self.VOLUME_BOUNDARIES.append(vol.start)

        # deal with different types of volumes (i.e. partitions)
        # right now, just handle NTFS separately
        if vol.desc == 'NTFS / exFAT (0x07)' or vol.desc == 'NTFS (0x07)':
            logger.info("Creating SEV_NTFS_Sparse class from: %s" % vol.desc)
            self.vol_to_se[vol] = SEV_NTFS_Sparse(self.img, self.VOL_INFO, vol, self.url)
        else:
            self.vol_to_se[vol] = None
    
    
    ### TODO Go through this        
    def _get_volume(self, sector):
        """
            Will return the volume associated with a particular sector
        """
        import bisect

        idx = bisect.bisect(self.VOLUME_BOUNDARIES, sector)
        if idx > len(self.VOLUMES):
            return None
        else:
            return self.VOLUMES[idx - 1]


    def get_access(self, sector, sector_count, direction, data):
        """
            This function will resolve the volume that this sector is associated
            with and return the semantic access for that volume
        """
        vol = self._get_volume(sector)

        if vol is not None:
            SE = self.vol_to_se[vol]
            if SE is not None:
                return SE.get_access(sector, sector_count, direction, data)
            else:
                return None
        else:
            return None

    def dump_cache(self):
        """ Returns dictionary of vol.start -> cache """
        ret = {}
        for vol in self.VOLUMES:
            ret[vol.start] = self.vol_to_se[vol].dump_cache()
        
        return ret
                
    def print_mft(self):
        """
            Prints the MFT for all NTFS volumes
        """
        for vol in self.VOLUMES:
            if vol.desc == 'NTFS / exFAT (0x07)':
                sem_eng_vol = self.vol_to_se[vol]
                sem_eng_vol._print_mft()

    def get_error_logs(self):
        """
            Returns error logs for each volume
        """
        
        error_logs = {}
        
        for vol in self.VOLUMES:
            sem_eng_vol = self.vol_to_se[vol]
            
            if sem_eng_vol.get_error_log():
                error_logs[vol.desc] = sem_eng_vol.get_error_log()
            else:
                error_logs[vol.desc] = None
                
        return error_logs


class SemanticEngineVolumeSparse:
    """
        Base class for representing a semantic volume
    """
    
    def __init__(self, img, vol_info, volume, url):
        
        self.URL = url
        self.VOL_INFO = vol_info
        self.VOLUME = volume
        self.SECTOR_SIZE = self.VOL_INFO.info.block_size
        self.VOLUME_OFFSET = volume.start # Stored in SECTORS!
        self.OFFSET_BYTES = self.SECTOR_SIZE * self.VOLUME.start

        #self.IMG = Shadow_Img_Info(url=url,sector_size=self.SECTOR_SIZE)
        self.IMG = Write_Img_Info(url=url, sector_size=self.SECTOR_SIZE)
        
        self.error_log = []
 
    def get_error_log(self):
        return self.error_log
 
    def get_access(self, sector, sector_count, direction, data, depth=0):
        print "get_access() should be overridden!"
    
    def _is_file_allocated(self, tsk_fs_file):
        """
        Returns true if file is currently allocated, otherwise false
        """
        
        ## need to check the flags field -- tsk_fs_file.meta.flags
        
#        return (not tsk_fs_file.meta) or (tsk_fs_file.meta.flags & pytsk3.TSK_FS_META_FLAG_ALLOC != 0)
        return (long(str(tsk_fs_file.meta.flags)) & pytsk3.TSK_FS_META_FLAG_ALLOC) != 0
    
    def dump_cache(self):
        return self.IMG.dump_cache()


class SEV_NTFS_Sparse(SemanticEngineVolumeSparse):
    """
        Generic class for handling types of volumes/partitions supported by pyTSK (slow but should work)
    """

    def __init__(self, img, vol_info, volume, url):
        """
            Intiialize our NTFS volume
        """
        SemanticEngineVolumeSparse.__init__(self, img, vol_info, volume, url)

        # Try to open the file system
        try:
            self.FILE_SYSTEM = pytsk3.FS_Info(self.IMG, self.OFFSET_BYTES, pytsk3.TSK_FS_TYPE_DETECT)
        except IOError:
            # If we couldn't find a file system, return None
            logger.error( "Could not load file system with pyTSK at offset %d" % self.VOLUME_OFFSET)
            return None

        
        # inode mappings
        self.fs_sector_to_inode = {}
        self.fs_inode_to_path = {}
        #Contains the mappings for our resident attributes
        self.fs_inode_to_sector_resident = {}
        #Contains the sectors that make up the MFT entries (and consqeuently the resident attributes)
        
        self.mft_raw = None

        # Extract useful infor about the file system
        self.ROOT_INUM = self.FILE_SYSTEM.info.root_inum
        first_inum = self.FILE_SYSTEM.info.first_inum
        self.LAST_INUM = self.FILE_SYSTEM.info.last_inum
        self.OFFSET = self.FILE_SYSTEM.info.offset
        self.BLOCK_COUNT = self.FILE_SYSTEM.info.block_count
        self.BLOCK_SIZE = self.FILE_SYSTEM.info.block_size
        
        # Get our MFT offset (in Blocks)
        self.MFT = self.FILE_SYSTEM.open_meta(inode=0)
        mft_offset = None
        for attr in self.MFT:
            if attr.info.type == pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA:
                for run in attr:
                    if mft_offset is None or run.addr < mft_offset:
                        mft_offset = run.addr
                    
                
        # Store our MFT offset in sectors (mft offset in volume + volume offset)
        self.MFT_OFFSET = self._block_to_sectors(mft_offset)[0]
        '''
        print("Root: %s" % self.BLOCK_SIZE)
        print("First: %s" % first_inum)
        print("Last: %s" % self.LAST_INUM)
        print("Offset: %s" % self.OFFSET)
        print("Block Size: %d" % self.BLOCK_SIZE)
        print("MFT Offset: %d" % self.MFT_OFFSET)
        '''
        ## Step 3: Open the directory node this will open the node based on path
        ## or inode as specified.
        self._load_file_system()

        ## Testing MFT Resident Attribute sector location to inode relationship
        ## Get MFT Sector Ranges
        

    def _get_mft_sectors(self):
        mft_sectors = []
        for key,value in self.fs_sector_to_inode.iteritems():
            if(value == 0 ):
                mft_sectors.append(key)
        return _mft_sectors

    def _print_mft(self):
        """
            Function to print our MFT out to stdout
        """
        root_dir = self.FILE_SYSTEM.open_dir(inode=self.ROOT_INUM)
        self.fs_inode_to_path[self.ROOT_INUM] = "/"
        self._parse_paths(root_dir,"/")
        
        last_inum = self.FILE_SYSTEM.info.last_inum
        for inode_num in xrange(0, last_inum+1):
            f = self.FILE_SYSTEM.open_meta(inode=inode_num)
            
            filename = 'None'
            if inode_num in self.fs_inode_to_path:
                filename = self.fs_inode_to_path[inode_num]
            
            output = "%d  %s " % (inode_num, filename)
            
            for attribute in f:                    
                for run in attribute:
                    # run.addr should be the LBA
                    # TSK seems to use run.addr == 0 for sparse runs too
                    # but this can mess up $Boot, whose addr is also 0, so we have to special case it
                    if run.addr != 0 or (f.info.name and f.info.name.name == "$Boot"):
                        self._add_run(inode_num, run.addr, run.len)
                    output += str([run.len, run.addr]) + " "
                    
        
            print output
        
    
    def _load_file_system(self):
        """
        Parse all the MFT entries
        """
        
        #a = time.time()
        # parse the paths so we get full paths
        root_dir = self.FILE_SYSTEM.open_dir(inode=self.ROOT_INUM)
        self.fs_inode_to_path[self.ROOT_INUM] = "/"
        self._parse_paths(root_dir,"/")
        
        #print "Total time to process path structure: %f s" % (time.time() - a)
        logger.info("Parsing MFT Entries")
        # parse all the MFT entries in order
        last_inum = self.FILE_SYSTEM.info.last_inum
        for inode_num in xrange(0, last_inum+1):
            self._load_file_entry(inode_num)
            


    def _parse_paths(self, directory, parent_path=""):
        """
        Parse the full paths of our file entries
        """
        
        for f in directory:
            
            filename = f.info.name.name
            
            if filename in [".", ".."]:
                continue
            abs_filename = os.path.join(parent_path,filename)    
            # add to our inode -> path mapping if this file entry has an MFT number
            if f.info.meta:
                inode = f.info.meta.addr
                self.fs_inode_to_path[inode] = abs_filename
                    
            if f.info.name.type == pytsk3.TSK_FS_NAME_TYPE_DIR and f.info.meta:
                self._parse_paths(f.as_directory(), parent_path=abs_filename)


    def _get_path(self, raw_mft, inode):
        """
        Tries to parse out the path for this file given the raw MFT record
        using mft.parse_record
        """
           
        if raw_mft is None:
            logger.debug("get_path: Got empty raw_mft, returning None")
            return None
        
        raw_mft_record = raw_mft[inode*1024:(inode+1)*1024]
        
        if len(raw_mft_record) < 4:
            logger.warn("Got empty mft record for inode #%d"%inode)
            return None
         
        if(len(raw_mft_record) != 1024):
            self.fs_inode_to_path[inode] = 'NoFNRecord'
            return self.fs_inode_to_path[inode]
            
        record = mft.parse_record(raw_mft_record, mft.set_default_options())
        
        if record['fncnt'] == 1:
            record['par_ref'] = record['fn',0]['par_ref']
            record['name'] = record['fn',0]['name']
        if record['fncnt'] > 1:
            record['par_ref'] = record['fn',0]['par_ref']
            for j in (0, record['fncnt']-1):
                if (record['fn', j]['nspace'] == 0x1 or record['fn', j]['nspace'] == 0x3):
                    record['name'] = record['fn', j]['name']
            if (record.get('name') == None):
                record['name'] = record['fn', record['fncnt']-1]['name']
        
        if 'name' not in record:
            self.fs_inode_to_path[inode] = 'NoFNRecord' 
            return self.fs_inode_to_path[inode]    
            
        filename = record['name']

        # now go up the chain of parent pointers, if needed
        try:
            if record['par_ref'] == 5: # 5 is "/", the root directory
                self.fs_inode_to_path[inode] = os.path.join('/',filename) 
                return self.fs_inode_to_path[inode]
        
        except: # If there was an error getting the parent's sequence number, then there is no FN recor
            self.fs_inode_to_path[inode] = 'NoFNRecord'
            return self.fs_inode_to_path[inode]
                
        # Self referential parent sequence number. The filename becomes a NoFNRecord note
        if (record['par_ref']) == inode:
            print("Error, self-referential, while trying to determine path for inode %s" % inode)
            self.fs_inode_to_path[inode] = 'ORPHAN/' + filename
            return self.fs_inode_to_path[inode]
        
        # We're not at the top of the tree and we've not hit an error
        parentpath = self._get_path(raw_mft, record['par_ref'])
        self.fs_inode_to_path[inode] = os.path.join(parentpath, filename)
        
        return self.fs_inode_to_path[inode]

    
    def _clean_file_entry(self, inode_num):
        """
        Cleans up block mappings for this file entry
        in preparation for reloading
        """
        # open up the file entry by inode number
        f = self.FILE_SYSTEM.open_meta(inode=inode_num)
        
        # skip deleted files
#         if not self._is_file_allocated(f.info):
#             print("Skip cleaning file inode %d" % inode_num)
#             return
        
        # remove block mappings
        for attribute in f:
            for run in attribute:
                self._remove_run(inode_num, run.addr, run.len)
        
        
    
    def _load_file_entry(self, inode_num):
        """
        Reload and reprocess a file entry by inode_num
        """
        # add the sectors inside the MFT for this inode too
        sectors = self._mft_record_to_sectors(inode_num)
        
        # open up the file entry by inode number
        f = self.FILE_SYSTEM.open_meta(inode=inode_num)
        
        # skip deleted files
#         if not self._is_file_allocated(f.info):
#             print("Skip loading file inode %d" % inode_num)
#             return
        
        filename = 'None'
        if inode_num in self.fs_inode_to_path:
            filename = self.fs_inode_to_path[inode_num]
        output = "%d  %s " % (inode_num, filename)
        
        for attribute in f:
                #print("Attribute:")
                #print("Name: %s" % attribute.info.name)
                #print("ID: %d" % attribute.info.id)
                #print("Size: %d" % attribute.info.size)
                
                for run in attribute:
                    #print("Run:")
                    #print("Offset: %d" % run.offset)
                    #print("Address: %d" % run.addr)
                    #print("Length: %d" % run.len)
                    #print("Flags: %s" % run.flags)
                    
                    # run.addr should be the LBA
                    # TSK seems to use run.addr == 0 for sparse runs too
                    # but this can mess up $Boot, whose addr is also 0, so we have to special case it
                    if run.addr != 0 or (f.info.name and f.info.name.name == "$Boot"):
                        self._add_run(inode_num, run.addr, run.len)                            
                        
                        output += str([run.len, run.addr]) + " "


    def _reload_file_entry(self, inode_num):
        """
        Reload a file entry if by its inode if we know it has been updated
        """
        self._clean_file_entry(inode_num)
        self._load_file_entry(inode_num)


    def _remove_run(self, inode_num, addr, length):
        """
        Remove a data run
        """
        # check for out of bounds
        if (length < 0 or length > self.BLOCK_COUNT) or \
           (addr < 0 or addr+length > self.BLOCK_COUNT):                
            self.error_log.append({'error_type':'datarun_out_of_bounds', 'MFT Record Number':inode_num, 'data_run':{'num_blocks':length, 'addr':addr}})
            return
        
        # Add all of our sector mappings
        for i in range(length):    
            for sector in self._block_to_sectors(addr+i):
                if sector in self.fs_sector_to_inode:
                    del self.fs_sector_to_inode[sector]


    def _add_run(self, inode_num, block_addr, length):
        """
            Add a run and annotate all of the sectors that this file touches
            
            @param inode_num: TSK inode number (aka MFT entry number) 
            @param block_addr: block offset on volume to this run
            @param length: length of run in blocks
        """
        
        # check for out of bounds
        if (length < 0 or length > self.BLOCK_COUNT) or (block_addr < 0 or block_addr+length > self.BLOCK_COUNT):                
            self.error_log.append({'error_type':'datarun_out_of_bounds', 'MFT Record Number':inode_num, 'data_run':{'num_blocks':length, 'block_addr':block_addr}})
            return
            
        # 
        for i in range(length):
            for sector in self._block_to_sectors(block_addr+i):
            
                # check for a collision
                if sector in self.fs_sector_to_inode:
                    # filter out special metafiles
                    inode2 = self.fs_sector_to_inode[sector]
                    
                    f1_name = ""
                    if inode_num in self.fs_inode_to_path:
                        f1_name = self.fs_inode_to_path[inode_num]

                    f2_name = ""
                    if inode2 in self.fs_inode_to_path:
                        f2_name = self.fs_inode_to_path[inode2]
                    
                    # check that the inodes (MFT record number for NTFS) are not the same
                    if inode_num != inode2:
                        
                        # dealing with special case of $BadClus
                        if f1_name != "" and f1_name[1] != '$' and f2_name != "" and f2_name[1] != '$':
                        
                            logger.error( "Datarun collision for MFT record no %d and MFT record no %d at block %d." % (inode_num, inode2, block_addr+i))
                            #print "Datarun collision for MFT record no %d and MFT record no %d at block %d." % (inode_num, inode2, block_addr+i)
                            
                            self.error_log.append({'error_type':'datarun_collision', 
                                               'filename1':f1_name, 
                                               'inode1':inode_num, 
                                               'filename2':f2_name,
                                               'inode2':inode2, 
                                               'block_addr':block_addr+i})
                            continue
                
                self.fs_sector_to_inode[sector] = inode_num


    def get_access(self, sector, sector_count, direction, data):
        
        # return structure
        # Fields:
        #  Sector address
        #  op - read, write
        #  type - mft_data, nonres_metadata, nonres_data, unknown
        #  mft_record - MFT record no, if known
        #  raw_data - the raw data
        #  semantic_data - some semantic info, mostly for metadata writes
        
        
        # Types of operations
        # [MFT READ]
        # [MFT WRITE]
        # [CONTENT READ]
        # [CONTENT WRITE]
        # [FILE CREATED]
        # [FILE DELETED]
        # [FILE MOVED]
        # [MBR READ]
        # [MBR WRITE]
        # [TIMESTAMP ROLLBACK]
        # [FILE HIDDEN]
        # [UNKONWN READ]
        # [UNKONWN WRITE]
        
        filesystem_operations = []
        
        
        
        # If there were any WRITEs, need to apply changes to metadata
        # for shadow data structures
        #print direction
        if direction == G.SATA_OP.DIRECTION.WRITE:
        #    print "Write operation!!!"
            updated_mft_entries = {}

            # See if these are MFT updates
            inodes = self._get_records_from_sectors(range(sector, sector+sector_count))
            for inode in inodes:
                try:    
                    f = self.FILE_SYSTEM.open_meta(inode=inode)
                    updated_mft_entries[inode] = f
                except:
                    logger.error("Possible Corrupted MFT entry found at inode: %d" % inode)
                    #print "Possible corrupted MFT entry found at inode: %d" % inode
            # Save our last inum
            self.LAST_INUM = self.FILE_SYSTEM.info.last_inum

            
            # apply changes only if this was an MFT Update
            if len(updated_mft_entries) > 0:
                # Save old MFT
                self.old_mft_raw = self.mft_raw
                
                # Update file system
                self._update_file_system(sector, sector_count, data)
                
                # Extract new MFT
                mft_file = self.FILE_SYSTEM.open_meta(inode=0)
                self.mft_raw = mft_file.read_random(0,mft_file.info.meta.size)


            # determine if there are new MFT records to reload
            if self.LAST_INUM < self.FILE_SYSTEM.info.last_inum:
                # Reparse the whole directory structure
                """
                    @TODO Optimize this so that we only parse the new inode
                    and extract the path using analyzeMFT code.
                """
                root_dir = self.FILE_SYSTEM.open_dir(inode=self.ROOT_INUM)
                self.fs_inode_to_path[self.ROOT_INUM] = "/"
                self._parse_paths(root_dir,"/")
                
            # Add all of the new inode entries to be reported
            while self.LAST_INUM < self.FILE_SYSTEM.info.last_inum:
                self.LAST_INUM += 1
                self._load_file_entry(self.LAST_INUM)
                updated_mft_entries[self.LAST_INUM] = None

            self.LAST_INUM = self.FILE_SYSTEM.info.last_inum


            new_inodes = self._get_records_from_sectors(range(sector, sector+sector_count))
            for inode in new_inodes:
                if inode not in updated_mft_entries:
                    updated_mft_entries[inode] = None
            
#             # Update our internal data structures if necessary
            for record_no in updated_mft_entries:
                 # reload all the MFT records that were touched
                self._reload_file_entry(record_no)
                         
                 # Deal with file creation/deletion
                 # compare old and new record flags
                old_f = updated_mft_entries[record_no]
                new_f = self.FILE_SYSTEM.open_meta(inode=record_no)    
                if old_f is None:
                    break
                old_flags = long(str(old_f.info.meta.flags))
                new_flags = long(str(new_f.info.meta.flags))
 
                 # check for creation
                if (old_flags & pytsk3.TSK_FS_META_FLAG_ALLOC == 0) and (new_flags & pytsk3.TSK_FS_META_FLAG_ALLOC != 0):
                    sectors = self._mft_record_to_sectors(record_no)
                    filename = "unknown"
                    if record_no in self.fs_inode_to_path:
                        filename = self.fs_inode_to_path[record_no]
                         
                    filesystem_operations.append(self._fs_operation(sectors[0], 
                                                     'WRITE',
                                                     '[FILE CREATED]', 
                                                     record_no, 
                                                     filename, 
                                                     ''))
                 # check for deletion
                elif (old_flags & pytsk3.TSK_FS_META_FLAG_UNALLOC == 0) and (new_flags & pytsk3.TSK_FS_META_FLAG_UNALLOC != 0):
                    sectors = self._mft_record_to_sectors(record_no)
                    filename = "unknown"
                    if record_no in self.fs_inode_to_path:
                        filename = self.fs_inode_to_path[record_no]
                         
                    filesystem_operations.append(self._fs_operation(sectors[0], 
                                                     'WRITE',
                                                     '[FILE DELETED]', 
                                                     record_no, 
                                                     filename, 
                                                     ''))
                else:
                    pass

            
            # Look at the writes again semantically and add them to our output structure            
            for i in xrange(sector_count):
                # KNOWN WRITE
                if sector+i in self.fs_sector_to_inode:
                    
                    inode = self.fs_sector_to_inode[sector+i]
                    
                    filename = "unknown"
                    
                    op_type = ''
                    semantic_data = []
                    raw_data = data[i*self.SECTOR_SIZE:(i+1)*self.SECTOR_SIZE]
                    
                    if inode in self.fs_inode_to_path:                
                        filename = self.fs_inode_to_path[inode]
                    else:
                        f = self.FILE_SYSTEM.open_meta(inode=inode)
                        #filename = "UNKNOWN_PREFIX "
                        if f.info.name:
                            filename = f.info.name.name
                            
                        
                    if inode == 0:
                        op_type = "[MFT WRITE]"
                        record_calc = (sector+i - 786431)/1024
                        
                        #print "Record: %d %d, Sector: %d"%(inode, record_calc, sector+i)
                        
                        #print updated_mft_entries
                        
                        for record_no in updated_mft_entries:
                            # do the diff
                            old_f = updated_mft_entries[record_no]
                            new_f = self.FILE_SYSTEM.open_meta(inode=record_no)
                            meta_diff = self._diff_metadata(old_f, new_f,record_no)
                            semantic_data.append(meta_diff)
                        
                    elif sector+i == 1 or sector+i == 0:
                        op_type = "[MBR WRITE]"
                    else:
                        op_type = "[CONTENT WRITE]"
                        
                       
                    
                    #Check if we are playing with a resident attribute
                    if inode == 0:
                        if sector+i in self.fs_inode_to_sector_resident:
                            if self.fs_inode_to_sector_resident[sector+i] in self.fs_inode_to_path:
                                res_inode = self.fs_inode_to_sector_resident[sector+i]
                                res_filename = self.fs_inode_to_path[res_inode]
                                filename = filename + " entry for " + res_filename
                    filesystem_operations.append(self._fs_operation(sector+i, 
                                                                    'WRITE', 
                                                                    op_type, 
                                                                    inode, 
                                                                    filename, 
                                                                    raw_data,
                                                                    semantic_data))
                # UNKNOWN WRITE
                else:
                    filesystem_operations.append(self._fs_operation(sector+i, 
                                                    'WRITE', 
                                                    '[UNKNOWN WRITE]', 
                                                    '[unknown inode]', 
                                                    'unknown', 
                                                    data[i*self.SECTOR_SIZE:(i+1)*self.SECTOR_SIZE]))
                    
                    
#                    print "UNKNOWN DATA sector %d: " % (sector+i)
#                    print data[i*self.SECTOR_SIZE:(i+1)*self.SECTOR_SIZE] #binascii.hexlify(data[i*self.SECTOR_SIZE:(i+1)*self.SECTOR_SIZE])

                
            
        else: # READs, just carry on as normally
            
            for i in xrange(sector_count):
                
                op_type = ''
                inode = 'unknown'
                filename = 'unknown'
                
                
                # Known Read
                if sector+i in self.fs_sector_to_inode:
                    inode = self.fs_sector_to_inode[sector+i]
                    
                    if inode in self.fs_inode_to_path:
                        filename = self.fs_inode_to_path[inode]
                    
                    if sector+i == 1:
                        op_type = "[MBR READ]"
                    elif inode == 0:
                        op_type = '[MFT READ]'
                        if sector+i in self.fs_inode_to_sector_resident:
                            if self.fs_inode_to_sector_resident[sector+i] in self.fs_inode_to_path:
                                res_inode = self.fs_inode_to_sector_resident[sector+i]
                                res_filename = self.fs_inode_to_path[res_inode]
                                filename = filename + "entry for " + res_filename
                    else:
                        op_type = '[CONTENT READ]'
        
                # Unknown read
                else:
                    op_type = '[UNKNOWN READ]'
                
                filesystem_operations.append(self._fs_operation(sector+i, 
                                                                'READ', 
                                                                op_type, 
                                                                inode,
                                                                filename, 
                                                                data[i*self.SECTOR_SIZE:(i+1)*self.SECTOR_SIZE]))
                
                
        return filesystem_operations


    def _fs_operation(self, sector, op, op_type, mft_record_no, filename, raw_data, semantic_data=''):
        return {'sector':sector,
                'op':op,
                'op_type':op_type,
                'inode':mft_record_no,
                'filename':filename,
                'raw_data':raw_data,
                'semantic_data':semantic_data}
        
        
    def _diff_metadata(self, old_file, new_file, inode):
        """
            This function will return an intelligent diff of the meta data
            associated with the given inode (MFT Record #)
            
            @param old_file: PyTSK file object for the old entry
            @param new_file: PyTSK file object for the new entry
            @param inode: Inode or Record number of the files
            @return: Some dict with intelligent diffing. 
            
            @TODO Finish this!!!!
            @bug: bit shifting for extracting flag values is currently wrong!
            They all evalutate 1 for some reason when the flags bitmask clearly 
            idicates they aren't
        """

        # Get our flags
        new_flags = long(str(new_file.info.meta.flags))
        mft_filename = self._get_path(self.mft_raw, inode)
            
        semantic_data_new = {
                                'filename':mft_filename,
                                'flags':new_flags,
                                # Extract Flags
                                'flag_alloc':new_flags & pytsk3.TSK_FS_META_FLAG_ALLOC,
                                'flag_comp':(new_flags & pytsk3.TSK_FS_META_FLAG_COMP) >> 4,
                                'flag_orphan':(new_flags & pytsk3.TSK_FS_META_FLAG_ORPHAN) >> 5,
                                'flag_unalloc':(new_flags & pytsk3.TSK_FS_META_FLAG_UNALLOC) >> 1,
                                'flag_unused':(new_flags & pytsk3.TSK_FS_META_FLAG_UNUSED) >> 3,
                                'flag_used':(new_flags & pytsk3.TSK_FS_META_FLAG_USED) >> 2,
                                'size':new_file.info.meta.size,
                                'uid':new_file.info.meta.uid,
                                'gid':new_file.info.meta.gid,
#                                 'hidden':new_file.info.meta.hidden,
                                'mtime':new_file.info.meta.mtime,
                                'mtime_nano':new_file.info.meta.mtime_nano,
                                'atime':new_file.info.meta.atime,
                                'atime_nano':new_file.info.meta.atime_nano,
                                'ctime':new_file.info.meta.ctime,
                                'ctime_nano':new_file.info.meta.ctime_nano,
                                'crtime':new_file.info.meta.crtime,
                                'crtime_nano':new_file.info.meta.crtime_nano,
                                'content_len':new_file.info.meta.content_len,
                                'seq':new_file.info.meta.seq,
                         }
        
        semantic_data = {
                            'inode':inode,
                            'filename':mft_filename,
                            'meta_data':semantic_data_new,
                            'changes':{}
                        }
        
        if old_file is not None:
            old_flags = long(str(old_file.info.meta.flags))
            old_mft_filename = self._get_path(self.old_mft_raw, inode)
            semantic_data_old = {
                                'filename':old_mft_filename,
                                'flags':old_flags,
                                # Extract flags
                                'flag_alloc':(old_flags & pytsk3.TSK_FS_META_FLAG_ALLOC),
                                'flag_comp':(old_flags & pytsk3.TSK_FS_META_FLAG_COMP) >> 4,
                                'flag_orphan':(old_flags & pytsk3.TSK_FS_META_FLAG_ORPHAN) >> 5,
                                'flag_unalloc':(old_flags & pytsk3.TSK_FS_META_FLAG_UNALLOC) >> 1,
                                'flag_unused':(old_flags & pytsk3.TSK_FS_META_FLAG_UNUSED) >> 3,
                                'flag_used':(old_flags & pytsk3.TSK_FS_META_FLAG_USED) >> 2,                                
                                'size':old_file.info.meta.size,
                                'uid':old_file.info.meta.uid,
                                'gid':old_file.info.meta.gid,
#                                 'hidden':old_file.info.meta.hidden,
                                'mtime':old_file.info.meta.mtime,
                                'mtime_nano':old_file.info.meta.mtime_nano,
                                'atime':old_file.info.meta.atime,
                                'atime_nano':old_file.info.meta.atime_nano,
                                'ctime':old_file.info.meta.ctime,
                                'ctime_nano':old_file.info.meta.ctime_nano,
                                'crtime':old_file.info.meta.crtime,
                                'crtime_nano':old_file.info.meta.crtime_nano,
                                'content_len':old_file.info.meta.content_len,
                                'seq':old_file.info.meta.seq
                                }
            
            for k in semantic_data_new:
                if semantic_data_new[k] != semantic_data_old[k] and semantic_data_old[k] is not None:
                    semantic_data['changes'][k] = {'new':semantic_data_new[k],
                                        'old':semantic_data_old[k]}
        else:
            # Just return the new ones
            semantic_data = dict(semantic_data.items() + 
                                 semantic_data_new.items())
        
        return semantic_data
            
        

    def _update_file_system(self, sector, sector_count, data):

        # update the shadow image
        self.IMG.write(sector, sector_count, data)
         
        # Reload our filesystem to wipe away caches
        self.FILE_SYSTEM = pytsk3.FS_Info(self.IMG, self.OFFSET_BYTES, pytsk3.TSK_FS_TYPE_DETECT)


    def _sector_to_block(self, sector):
        """
            Returns the block that the given sector is in
            
            @param sector: Sector to look up
            @return Block offset int this volume
        """
        # First remove our offset so that we are starting at 0 on the disk
        # On windows this is 63 sectors
        vs_byte_offset = (sector - self.VOLUME_OFFSET) * self.SECTOR_SIZE
        
        # Then figure out which block we fall in
        fs_block = vs_byte_offset / self.BLOCK_SIZE

        return fs_block


    def _block_to_sectors(self, block):
        """
            Returns list of sectors occupied by the block
        """
        
        # error check if sector is greater than a filesystem block
        assert self.SECTOR_SIZE <= self.BLOCK_SIZE
        
        # convert block to byte offset
        # block is given by offset from the volume
        vol_byte_offset = block * self.BLOCK_SIZE
        
        # VOLUME_OFFSET as provided by TSK's volume.start is in sectors not blocks
        abs_byte_offset = self.VOLUME_OFFSET*self.SECTOR_SIZE + vol_byte_offset
        
        start_sector = abs_byte_offset/self.SECTOR_SIZE
        
        return range(start_sector, start_sector + self.BLOCK_SIZE/self.SECTOR_SIZE)


    def _mft_record_to_sectors(self, record_no):
        """
            Given an MFT record number, returns the sectors
            that it occupies.
            
            Assumes that the MFT has been properly parsed!  Relies on record 0 ($MFT)
            being correct.
            
            FB Updates 10/17
            If an entry is very small and only contains an MFT entry, the actual filename
            is not collected when using the get_access function, the filename is listed as 
            /$MFT
        """
        
            
        mft_blocks = self._mft_dataruns()

        # byte offset for this record from start of the mft
        byte_offset_from_MFT_start = record_no * 1024    
        # go through each data run looking for the sector that
        # matches this byte offset
                
        bytes_left = byte_offset_from_MFT_start
        for (num_blocks, lba) in mft_blocks:
            
            # check if the record is in this datarun
            if bytes_left < num_blocks * self.BLOCK_SIZE:
    
                # record should be inside this block
                block = lba + bytes_left/self.BLOCK_SIZE
                 
                sectors = self._block_to_sectors(block)
                
                # find offset into this block
                byte_offset_into_block = bytes_left % self.BLOCK_SIZE
                sector_offset = byte_offset_into_block/self.SECTOR_SIZE
                
                sector_start = sectors[0] + sector_offset
                # 1.) Check if the sector resides in the MFT
                # 2.) If it does, add a new dictionary entry with the inode
                # 3.) That inode can later be mapped back to a file!
                if(sector_start in self.fs_sector_to_inode and self.fs_sector_to_inode[sector_start] == 0):
                    self.fs_inode_to_sector_resident[sector_start] = record_no
                    self.fs_inode_to_sector_resident[sector_start + 1024 / self.SECTOR_SIZE] = record_no
                return range(sector_start, sector_start+1024/self.SECTOR_SIZE)

                
            else:
                bytes_left -= num_blocks * self.BLOCK_SIZE
        
        # we only get here if record_no is too high to actually be in the MFT    
        return []
    
    
    def _get_records_from_sectors(self,sectors):
        """
            Will return the inode number of a sector if it's in the MFT
            or None otherwise.
            
            @param sector: List of physical sectors
            @return List of MFT Record #s (AKA inode number in pytsk) or empty list 
        """
        
        inode_start = 0
        
        inodes = []
        # Loop over all of the MFT runs in order
        for (num_blocks, block_addr) in self._mft_dataruns():
            
            # Get our actual start and ending sectors of this MFT run
            sector_start = self._block_to_sectors(block_addr)[0]
            sector_end = sector_start + (num_blocks*self.BLOCK_SIZE)/self.SECTOR_SIZE
            
            
            for sector in sectors:
                # Is the sector in this data run?
                if sector >= sector_start and sector <= sector_end:
                    # First inode num in this run + our offset
                    record_num = inode_start + ((sector - sector_start)*self.SECTOR_SIZE)/MFT_ENTRY_SIZE
            
                    if record_num not in inodes:
                        inodes.append(record_num)
            
            # Add all of the inodes that we just skipped
            inode_start += ((sector_end - sector_start)*self.SECTOR_SIZE)/MFT_ENTRY_SIZE
            
        return inodes
        
        

        
    
    def _mft_dataruns(self):
        """
            Returns a list of all of the data runs in the MFT
            
            @return list of tuples (run length, block address)
        """
        # get inode 0
        self.MFT = self.FILE_SYSTEM.open_meta(inode=0)
        
        mft_blocks = []
        for attribute in self.MFT:
            if attribute.info.type == pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA:
                for run in attribute:
                    mft_blocks.append((run.len, run.addr))
                    
        return sorted(mft_blocks, key=lambda tup: tup[1])
    
    
        

    def _is_MFT_data(self, data):
        """
        Peeks into start of the data and determines if it contains MFT data
        
        Based on whether MFT header is present
        """
        
        magic_number = struct.unpack("<I", data[:4])[0]
        
        return (magic_number == 0x46494C45 or # FILE
                magic_number == 0x44414142) # BAAD


