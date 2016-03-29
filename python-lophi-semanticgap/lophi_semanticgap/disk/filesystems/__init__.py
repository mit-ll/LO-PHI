"""
Classes for representing Disks and Volumes semantically to help us bridge the semantic gap
from raw data
"""
import os
import struct
import sys
import logging

# 3rd Party
import pytsk3

# Append our system path (FOR DEVLEOPMENT ONLY)
sys.path.append(os.path.join(os.getcwd(), "../../"))

# LO-PHI
import lophi.globals as G
from lophi_semanticgap.disk.filesystems.ntfs import MftSession, mft

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Shadow_Img_Info(pytsk3.Img_Info):
    """
    Creates an updateable Img_Info that maintains a shadow copy in memory.
    No changes are made to the underlying disk image.
    """
    
    def __init__(self, url, sector_size):
        self.URL = url
        self.SECTOR_SIZE = sector_size
        
        ## Open the image
        self.fd = open(url, 'rb')
        if not self.fd:
            raise IOError("Unable to open %s" % url)

        ## data cache in sectors
        self.CACHE = {}

        ## Call the base class with an empty URL
        pytsk3.Img_Info.__init__(self, '')

    def get_size(self):
        """ This function returns the size of the image """
        return os.path.getsize(self.URL)

    def read(self, off, length):
        """
        This returns byte ranges from the image, using the image
        Returns data from cache first
        """
        
        data = []
        
        # Read sector by sector
        
        while length > 0:
            
            # determine which sector
            sector = off/self.SECTOR_SIZE
            
            # determine the offset --> should be 0 when we get sector aligned
            offset_into_sector = off % self.SECTOR_SIZE
            
            # determine the length to read, at most one sector at a time
            l = min(length, self.SECTOR_SIZE - offset_into_sector)
            
            # read the data
            data.append(self._read_sector(sector, offset_into_sector, l))
            
            # update the length left and the offset
            off += l
            length -= l
                    
        return ''.join(data)


    def _read_sector(self, sector, offset_into_sector, length):
        """
        Reads a single sector with offset into the sector and length
        """
                
        # determine if the sector is in the CACHE
        if sector in self.CACHE:
#            print "Reading sector %d from CACHE" % sector
            return self.CACHE[sector][offset_into_sector:offset_into_sector+length]
        else:
#            print "Reading sector %d from DISK" % sector
            self.fd.seek(sector*self.SECTOR_SIZE + offset_into_sector)
            return self.fd.read(length)
        

    def write(self, sector, sector_count, data):
        """ Writes data to the cache """
        #print "Writing sectors %d to %d to CACHE" % (sector, sector+sector_count-1)
        for i in xrange(sector_count):    
            self.CACHE[sector+i] = data[i*self.SECTOR_SIZE:(i+1)*self.SECTOR_SIZE]


    def close(self):
        """ This is called when we want to close the image """
        self.fd.close()
        
    def dump_cache(self):
        """ This is called when we want to dump the cache """
        return self.CACHE


class SemanticEngineDisk:
    
    """
        Base class for representing a disk containing SemanticEngineVolumes
    """

    
    def __init__(self, url):
        # parse out the different volumes
        
        self.url = url
        self.img = pytsk3.Img_Info(url=self.url)
        self.VOL_INFO = pytsk3.Volume_Info(self.img)

        self.vol_to_se = {}
        self.VOLUMES = []
        self.VOLUME_BOUNDARIES = []

        # print out some info about the disk image
        logger.debug("--- Volume info ---")
        logger.debug("Current: %d" % self.VOL_INFO.current)
        logger.debug("VS Type: %d" % self.VOL_INFO.info.vstype)
        logger.debug("Offset: %d" % self.VOL_INFO.info.offset)
        logger.debug("Block Size: %d" % self.VOL_INFO.info.block_size)
        logger.debug("Endian: %d" % self.VOL_INFO.info.endian)
        logger.debug("Partition List: %s" % self.VOL_INFO.info.part_list)
        logger.debug("Parition Count: %d" % self.VOL_INFO.info.part_count)
        logger.debug("--- Volume info ---")

        # Add each volume
        for vol in self.VOL_INFO:
            #print part.addr, part.desc, part.start, part.len
            self.add_volume(vol)

                
    def add_volume(self, vol):
        """
            Add a new volume
            
            WARNING: These must be added in sequential order!
        """
        logger.debug("--- Partition ---")
        logger.debug("Start: %d" % vol.start)
        logger.debug("Length: %d" % vol.len)
        logger.debug("Description: %s" % vol.desc)
        logger.debug("Address: %d" % vol.addr)
        logger.debug("Flags: %d" % vol.flags)

        
        type = vol.desc.split(" ")[0]
        self.VOLUMES.append(vol)
            
#            offset_bytes = self.VOL_INFO.info.block_size * vol.start
            
        self.VOLUME_BOUNDARIES.append(vol.start)

        # deal with different types of volumes (i.e. partitions)
        # right now, just handle NTFS separately
        if vol.desc == 'NTFS (0x07)':
            sev = SemanticEngineVolumePyTSK_NTFS(self.img, self.VOL_INFO, vol, self.url)
            if sev.NON_FILESYSTEM:
                self.vol_to_se[vol] = None
            else:
                self.vol_to_se[vol] = sev
        else:
            sev = SemanticEngineVolumePyTSK(self.img, self.VOL_INFO, vol, self.url)
            if sev.NON_FILESYSTEM:
                self.vol_to_se[vol] = None
            else:
                self.vol_to_se[vol] = sev
    
    
    ### TODO Go through this        
    def _get_volume(self, sector):
        import bisect

        idx = bisect.bisect(self.VOLUME_BOUNDARIES, sector)
        if idx > len(self.VOLUMES):
            return None
        else:
            return self.VOLUMES[idx - 1]


    def get_access(self, sector, sector_count, direction, data):
#        print "get_access: ", sector, sector_count, direction
        vol = self._get_volume(sector)

        if vol is not None:
            SE = self.vol_to_se[vol]
 #           rtn = {'Volume': vol, 'Semantic':None}
            if SE is not None:
                return SE.get_access(sector, sector_count, direction, data)
            else:
                # No semantic data for this write
                op = {}
                if direction == G.SATA_OP.DIRECTION.WRITE:
                    op['op'] = 'WRITE'
                else:
                    op['op'] = 'READ'

                op['op_type'] = '[NON FILESYSTEM]'
                op['filename'] = '[n/a non filesystem]'
                op['inode'] = '[n/a non filesystem]'
                op['sector'] = sector
                op['raw_data'] = data
                
                return [op]
        else:
            return None

    def dump_cache(self):
        """ Returns dictionary of vol.start -> cache """
        ret = {}
        for vol in self.VOLUMES:
            ret[vol.start] = self.vol_to_se[vol].dump_cache()
        
        return ret
                
    def print_mft(self):
        for vol in self.VOLUMES:
            if vol.desc == 'NTFS (0x07)':
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



class SemanticEngineVolume:
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

        self.IMG = Shadow_Img_Info(url=url,sector_size=self.SECTOR_SIZE)

        # error condition if pytsk cannot parse the filesystem
        self.NON_FILESYSTEM = False
        
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
    

class SemanticEngineVolumePyTSK(SemanticEngineVolume):
    """
        Generic class for handling types of volumes/partitions supported by pyTSK (slow but should work)
    """

    UPDATE_FILES = ['$MFT']

    def __init__(self, img, vol_info, volume, url):

        SemanticEngineVolume.__init__(self, img, vol_info, volume, url)

        # Try to open the file system
        try:
            file_system = pytsk3.FS_Info(self.IMG, self.OFFSET_BYTES, pytsk3.TSK_FS_TYPE_DETECT)
        except IOError:
            # If we couldn't find a file system, return None
            logger.error("Could not load file system with pyTSK at offset %d" % self.VOLUME_OFFSET)
            self.NON_FILESYSTEM = True
            return

        self.fs_block_to_file = {}
        self.fs_file_to_path = {}
        self.FILE_SYSTEM = file_system

        self.ROOT_INUM = file_system.info.root_inum
        first_inum = file_system.info.first_inum
        last_inum = file_system.info.last_inum
        offset = file_system.info.offset
        self.BLOCK_COUNT = file_system.info.block_count
        self.BLOCK_SIZE = file_system.info.block_size

#         print "Root: %s" % self.BLOCK_SIZE
#         print "First: %s" % first_inum
#         print "Last: %s" % last_inum
#         print "Offset: %s" % offset
# 
#         print "Block Size: %d" % self.BLOCK_SIZE
#         print file_system.info.first_block


        logger.debug("Root: %s" % self.BLOCK_SIZE)
        logger.debug("First: %s" % first_inum)
        logger.debug("Last: %s" % last_inum)
        logger.debug("Offset: %s" % offset)

        logger.debug("Block Size: %d" % self.BLOCK_SIZE)
        logger.debug(file_system.info.first_block)

        ## Step 3: Open the directory node this will open the node based on path
        ## or inode as specified.
        directory = file_system.open_dir(inode=self.ROOT_INUM)
        self._scan_file_system(directory)
        

    def _scan_file_system(self, directory, path=""):

        if directory is None:
            if path != "":
                directory = self.FILE_SYSTEM.open_dir(path=path)
            else:
                directory = self.FILE_SYSTEM.open_dir(inode=self.ROOT_INUM)

        ## Step 4: Iterate over all files in the directory and print their
        ## name. What you get in each iteration is a proxy object for the
        ## TSK_FS_FILE struct - you can further dereference this struct into a 
        ## TSK_FS_NAME and TSK_FS_META structs.
        for f in directory:

            filename = f.info.name.name

            if filename in [".", ".."]:
                continue

            abs_filename = os.path.join(path, filename)
#            print "Processing ", abs_filename
#            print f.info.meta
#            string = f.info.meta.addr, f.info.meta.size, abs_filename, f.info.name.type, f.info.meta.content_len

#            logger.debug(string)
#            logger.debug(f.info.fs_info.offset)
#            logger.debug(f.info.fs_info.first_block)

#            print "State:", f.info.meta.attr_state
#            print "Addr: ", f.info.name.meta_addr

#            f.info.name.filename = abs_filename


            self._add_file(f, abs_filename)

#            self.lookup_block(f.info.name.meta_addr)

            if f.info.name.type == pytsk3.TSK_FS_NAME_TYPE_DIR and f.info.meta:
                self._scan_file_system(f.as_directory(), path=abs_filename)

    def _add_file(self, f, path):
        """
            Add a file object to our internal structures
        """

        filename = f.info.name.name

        logger.debug(f.info)

        self.fs_file_to_path[f] = path


#        output = path + " "

#        print "%s %d" % (filename, f.info.meta.addr)

        has_runs = False
        for attribute in f:
                logger.debug("Attribute:")
                logger.debug("Name: %s" % attribute.info.name)
                logger.debug("ID: %d" % attribute.info.id)
                logger.debug("Size: %d" % attribute.info.size)
                
                for run in attribute:
                    has_runs = True
                    logger.debug("Run:")
                    logger.debug("Offset: %d" % run.offset)
                    logger.debug("Address: %d" % run.addr)
                    logger.debug("Length: %d" % run.len)
                    logger.debug("Flags: %s" % run.flags)
                    
                    # run.addr should be the LBA
                    # TSK seems to use run.addr == 0 for sparse runs too
                    # but this can mess up $Boot, whose addr is also 0, so we have to special case it
                    if run.addr != 0 or filename == "$Boot":
                        self._add_run(f, run.addr, run.len)
    #                print run.type
    
#                    output += " [Len: %d, Offset: %d, Addr: %d]," % (run.len, run.offset, run.addr)
    
#                     run_next = run.next
#                     while run_next is not None:
#                         logger.debug("Run:")
#                         logger.debug("Offset: %d" % run_next.offset)
#                         logger.debug("Address: %d" % run_next.addr)
#                         logger.debug("Length: %d" % run_next.len)
#                         logger.debug("Flags: %d" % run_next.flags)
#                         self._add_run(f, run_next.addr, run_next.len)
#                         
# #                        output += " Len: %d, Offset: %d, Addr: %d" % (run_next.len, run_next.offset, run_next.addr)
#                         
#                         run_next = run_next.next


#        print output

# This doesn't work when f has no inf.meta member
#        if not has_runs and f.info.meta.size > self.BLOCK_SIZE:
#            print "Where is this extra DATA?!?!?"
#            sys.exit(0)

    def _add_run(self, f, block_addr, length):
        """
            Add a run and annotate all of the sectors that this file touches
            
            @param f: TSK File Object
            @param block_addr: block offset on volume to this run
            @param length: length of run in blocks
        """
        
        # if f has a meta attribute, then its "inode" (MFT record no for NTFS) should be f.info.meta.block_addr
        
        for i in range(length):
            
            # check for out of bounds
            if (length < 0 or length > self.BLOCK_COUNT) or (block_addr < 0 or block_addr+length > self.BLOCK_COUNT):                
                self.error_log.append({'error_type':'datarun_out_of_bounds', 'filename':f.info.name.name, 'data_run':{'num_blocks':length, 'block_addr':block_addr}})
                continue
            
            
            
            # check for a collision
            if block_addr+i in self.fs_block_to_file:
                # filter out special metafiles
                f2 = self.fs_block_to_file[block_addr+i]
                
                if f.info.name.name[0] != '$' and f2.info.name.name[0] != '$':
                
                    # check that the inodes (MFT record number for NTFS) are not the same
                    
                    inode1 = ''
                    if f.info.meta:
                        inode1 = f.info.meta.addr
                        
                    inode2 = ''
                    
                    if f2.info.meta:
                        inode2 = f2.info.meta.addr
                    
                    if inode1 != '' and inode2 != '' and inode1 != inode2:
                    
                        logger.error("Datarun collision for file %s and file %s at block %d." % (f.info.name.name, self.fs_block_to_file[block_addr+i].info.name.name, block_addr+i))
                        
                        self.error_log.append({'error_type':'datarun_collision', 
                                           'filename1':f.info.name.name, 
                                           'inode1':inode1, 
                                           'filename2':self.fs_block_to_file[block_addr+i].info.name.name,
                                           'inode2':inode2, 
                                           'block_addr':block_addr+i})
                        continue
            
            self.fs_block_to_file[block_addr + i] = f

    def _sector_to_block(self, sector):

        # First remove our offset so that we are starting at 0 on the disk
        # On windows this is 63 sectors
        vs_byte_offset = (sector - self.VOLUME_OFFSET) * self.SECTOR_SIZE
        # Then figure out which block we fall in
        fs_block = vs_byte_offset / self.BLOCK_SIZE

        return fs_block



    def lookup_block(self, block):
        """
            Given a block on the filesystem, lookup the file
        """
#        print "lookup: %d" % block
        if block in self.fs_block_to_file:
            f = self.fs_block_to_file[block]
            return f
        else:
            return None


    def _update_file_system(self, sector, sector_count, data, file=None):

        # Reload our filesystem to wipe away caches
        #url = "/home/ch23339/WinXPSP3.img"
#        self.IMG = pytsk3.Img_Info(url)
#        self.FILE_SYSTEM = pytsk3.FS_Info(self.IMG, self.OFFSET_BYTES, pytsk3.TSK_FS_TYPE_DETECT)

        if file is not None:
            path = self.fs_file_to_path[file]
            new_file = self.FILE_SYSTEM.open(path)
#            print file.__dict__
#            print new_file.__dict__
        else:
            self._scan_file_system(None)

    def get_access(self, sector, sector_count, direction, data, depth=0):

#        if direction == G.SATA_OP.DIRECTION.READ:
        # See how many files were read
        files = []
        output_dict = {}
        i = 0
        first = True

        # Check all of the sectors that were affected
        while i < sector_count:

            # Convert to block and check to see if there is a file there
            fs_block = self._sector_to_block(sector + i)
            f = self.lookup_block(fs_block)

            # Only append each file once
            if f not in files and f is not None:
                files.append(f)

            if f:
                filename = self.fs_file_to_path[f]
                if filename in output_dict:
                    output_dict[filename]['blocks'].append(fs_block)
                else:
                    output_dict[filename] = {}
                    output_dict[filename]['blocks'] = [fs_block]

            # Increment into the next block
            if first:
                i += 1
                while fs_block == self._sector_to_block(sector + i) and i < sector_count:
                    i += 1
                first = False
            # If we are already on block boundaries just go straight to the next block
            else:
                i += self.BLOCK_SIZE / self.SECTOR_SIZE

#         if direction == G.SATA_OP.DIRECTION.WRITE and len(files) == 0 and depth == 0:
#             self._update_file_system(sector, sector_count, data)
#             return self.get_access(sector, sector_count, direction, data, depth=depth + 1)

        # Now put our results in a nice output format
        for f in files:
            if direction == G.SATA_OP.DIRECTION.READ:
#                print "READ: ", self.fs_file_to_path[f]
                
                output_dict[self.fs_file_to_path[f]]['op'] = 'READ'
                output_dict[self.fs_file_to_path[f]]['data'] = data
                
            else:
#                print "WRITE: ", self.fs_file_to_path[f]
                output_dict[self.fs_file_to_path[f]]['op'] = 'WRITE'
                output_dict[self.fs_file_to_path[f]]['data'] = data


                # Do we need to update and try again?
                if f.info.name.name in self.UPDATE_FILES and depth == 0:
                    self._update_file_system(sector, sector_count, data, file=f)
                    return self.get_access(sector, sector_count, direction, data, depth=depth + 1)


        return output_dict




class SemanticEngineVolumePyTSK_NTFS(SemanticEngineVolume):
    """
        Generic class for handling types of volumes/partitions supported by pyTSK (slow but should work)
    """

    def __init__(self, img, vol_info, volume, url):

        SemanticEngineVolume.__init__(self, img, vol_info, volume, url)

        # Try to open the file system
        try:
            self.FILE_SYSTEM = pytsk3.FS_Info(self.IMG, self.OFFSET_BYTES, pytsk3.TSK_FS_TYPE_DETECT)
        except IOError:
            # If we couldn't find a file system, return None
            logger.error("Could not load file system with pyTSK at offset %d" % self.VOLUME_OFFSET)
            self.NON_FILESYSTEM = True
            return

        
        # inode mappings
        self.fs_sector_to_inode = {}
        self.fs_inode_to_path = {}
        
        # maps sector to MFT record number if the sector
        # is inside the MFT
        self.sector_to_mft_record_no = {}

        self.ROOT_INUM = self.FILE_SYSTEM.info.root_inum
        first_inum = self.FILE_SYSTEM.info.first_inum
        self.LAST_INUM = self.FILE_SYSTEM.info.last_inum
        offset = self.FILE_SYSTEM.info.offset
        self.BLOCK_COUNT = self.FILE_SYSTEM.info.block_count
        self.BLOCK_SIZE = self.FILE_SYSTEM.info.block_size


        logger.debug("Root: %s" % self.BLOCK_SIZE)
        logger.debug("First: %s" % first_inum)
        logger.debug("Last: %s" % self.LAST_INUM)
        logger.debug("Offset: %s" % offset)

        logger.debug("Block Size: %d" % self.BLOCK_SIZE)

        ## Step 3: Open the directory node this will open the node based on path
        ## or inode as specified.
        self._load_file_system()

    def _print_mft(self):
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
        
        # parse all the MFT entries in order
        last_inum = self.FILE_SYSTEM.info.last_inum
        for inode_num in xrange(0, last_inum+1):
            self._load_file_entry(inode_num)
            


    def _parse_paths(self, directory, parent_path=""):
        """
        Parse the full paths of our file entries
        """
        
        if directory is None:
            if path != "":
                directory = self.FILE_SYSTEM.open_dir(path=path)
            else:
                directory = self.FILE_SYSTEM.open_dir(inode=self.ROOT_INUM)
        
        for f in directory:
            
            filename = f.info.name.name
            
            if filename in [".", ".."]:
                continue

            abs_filename = os.path.join(parent_path, filename)
            
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
        
        raw_mft_record = raw_mft[inode*1024:(inode+1)*1024]
        
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
            logger.debug("Error, self-referential, while trying to determine path for inode %s" % inode)
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
        if not self._is_file_allocated(f.info):
            #print "Skip cleaning file inode %d" % inode_num
            return
        
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
        for s in sectors:
            self.sector_to_mft_record_no[s] = inode_num
        
        # open up the file entry by inode number
        f = self.FILE_SYSTEM.open_meta(inode=inode_num)
        
        # skip deleted files
        if not self._is_file_allocated(f.info):
            #print "Skip loading file inode %d" % inode_num
            return
        
        filename = 'None'
        if inode_num in self.fs_inode_to_path:
            filename = self.fs_inode_to_path[inode_num]
        
        output = "%d  %s " % (inode_num, filename)
        
        for attribute in f:
                logger.debug("Attribute:")
                logger.debug("Name: %s" % attribute.info.name)
                logger.debug("ID: %d" % attribute.info.id)
                logger.debug("Size: %d" % attribute.info.size)
                
                for run in attribute:
                    logger.debug("Run:")
                    logger.debug("Offset: %d" % run.offset)
                    logger.debug("Address: %d" % run.addr)
                    logger.debug("Length: %d" % run.len)
                    logger.debug("Flags: %s" % run.flags)
                    
                    # run.addr should be the LBA
                    # TSK seems to use run.addr == 0 for sparse runs too
                    # but this can mess up $Boot, whose addr is also 0, so we have to special case it
                    if run.addr != 0 or (f.info.name and f.info.name.name == "$Boot"):
                        self._add_run(inode_num, run.addr, run.len)                            
                        
                        output += str([run.len, run.addr]) + " "
    #                print run.type
    
#        print output

# This doesn't work when f has no info.meta member
#        if not has_runs and f.info.meta.size > self.BLOCK_SIZE:
#            print "Where is this extra DATA?!?!?"
#            sys.exit(0)


    def _reload_file_entry(self, inode_num):
        """
        Reload a file entry if by its inode if we know it has been updated
        """
        #print "Reloading inode %d" % inode_num
        self._clean_file_entry(inode_num)
        self._load_file_entry(inode_num)

#         f = self.FILE_SYSTEM.open_meta(inode=inode_num)
#         
#         if f.info.name and f.info.name.type == pytsk3.TSK_FS_NAME_TYPE_DIR and f.info.meta:
#         
#             parent_path = os.path.dirname(self.fs_inode_to_path[inode_num])
#             self._parse_paths(f.as_directory(), parent_path)

    def _remove_run(self, inode_num, addr, length):
        """
        Remove a data run
        """
        
        for i in range(length):
            # check for out of bounds
            if (length < 0 or length > self.BLOCK_COUNT) or (addr < 0 or addr+length > self.BLOCK_COUNT):                
                self.error_log.append({'error_type':'datarun_out_of_bounds', 'MFT Record Number':inode_num, 'data_run':{'num_blocks':length, 'addr':addr}})
                continue
            
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
                
        for i in range(length):
            
            # check for out of bounds
            if (length < 0 or length > self.BLOCK_COUNT) or (block_addr < 0 or block_addr+length > self.BLOCK_COUNT):                
                self.error_log.append({'error_type':'datarun_out_of_bounds', 'MFT Record Number':inode_num, 'data_run':{'num_blocks':length, 'block_addr':block_addr}})
                continue
            
            
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
                        
                            logger.error("Datarun collision for MFT record no %d and MFT record no %d at block %d." % (inode_num, inode2, block_addr+i))
                            print "Datarun collision for MFT record no %d and MFT record no %d at block %d." % (inode_num, inode2, block_addr+i)
                            
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
        if direction == G.SATA_OP.DIRECTION.WRITE:
            
            old_records = {}
            mft_records_that_need_updating = set([])
            new_mft_records = set([])
        
            for i in xrange(sector_count):
                # determine which files we need to update
                if sector+i in self.fs_sector_to_inode:
                    
                    inode = self.fs_sector_to_inode[sector+i]
                    
                    mft_records_that_need_updating.add(inode)
                    if inode not in old_records:
                        f = self.FILE_SYSTEM.open_meta(inode=inode)
                        
                        # DO we need a copy of this?  There are pointers in this structure
                        old_records[inode] = f
                if sector+i in self.sector_to_mft_record_no:
                    # this sector is in the MFT itself
                    inode = self.sector_to_mft_record_no[sector+i]
                    
                    #print "MFT was touched at sector %d, inode %d" % (sector+i, inode)
                    
                    mft_records_that_need_updating.add(inode)
                    if inode not in old_records:
                        f = self.FILE_SYSTEM.open_meta(inode=inode)
                        
                        # DO we need a copy of this?  There are pointers in this structure
                        old_records[inode] = f
                    
                else:
                    pass
                    

            # apply changes
            self._update_file_system(sector, sector_count, data)

            # determine if there are new MFT records to reload
            if self.LAST_INUM < self.FILE_SYSTEM.info.last_inum:
                # Reparse the whole directory structure
                root_dir = self.FILE_SYSTEM.open_dir(inode=self.ROOT_INUM)
                self.fs_inode_to_path[self.ROOT_INUM] = "/"
                self._parse_paths(root_dir,"/")
            
            while self.LAST_INUM < self.FILE_SYSTEM.info.last_inum:
                self.LAST_INUM += 1
                self._load_file_entry(self.LAST_INUM)
                new_mft_records.add(self.LAST_INUM)

            if len(mft_records_that_need_updating) > 0:
                # Reparse all the filepath stuff
                root_dir = self.FILE_SYSTEM.open_dir(inode=self.ROOT_INUM)
                self.fs_inode_to_path[self.ROOT_INUM] = "/"

#                print "Need to reparse paths for inodes ", mft_records_that_need_updating
#                a = time.time()

                mft_file = self.FILE_SYSTEM.open_meta(inode=0)
                raw_mft = mft_file.read_random(0, mft_file.info.meta.size)
                for inode in mft_records_that_need_updating:
                    filename = self._get_path(raw_mft, inode)
#                    print "Filename for inode %d is %s" % (inode, filename)


#                print "Total time to open the raw $MFT and get the new paths: %f s" % (time.time() - a)


            # Update our internal data structures if necessary
            for record_no in mft_records_that_need_updating:
                # reload all the MFT records that were touched
                self._reload_file_entry(record_no)
                        
                # Deal with file creation/deletion
                # compare old and new record flags
                old_f = old_records[record_no]
                new_f = self.FILE_SYSTEM.open_meta(inode=record_no)

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
                    semantic_data = ''
                    raw_data = data[i*self.SECTOR_SIZE:(i+1)*self.SECTOR_SIZE]
                    
                    if inode in self.fs_inode_to_path:                
                        filename = self.fs_inode_to_path[inode]
                    else:
                        f = self.FILE_SYSTEM.open_meta(inode=inode)
                        #filename = "UNKNOWN_PREFIX "
                        if f.info.name:
                            filename = f.info.name.name
                    
                    if sector+i == 1:
                        op_type = "[MBR WRITE]"
                    elif inode in new_mft_records:
                        op_type = "[FILE CREATED]"
                    elif inode == 0:
                        op_type = "[MFT WRITE]"
                    else:
                        op_type = "[CONTENT WRITE]"
                        
                        # do the diff
                        old_record = old_records[record_no]
                        new_record = self.FILE_SYSTEM.open_meta(inode=record_no)
                        semantic_data = self._diff_metadata(old_record, new_record)
                    
                    
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
        
        
    def _diff_metadata(self, old_record, new_record):
        pass

    def _update_file_system(self, sector, sector_count, data):

        # update the shadow image
        self.IMG.write(sector, sector_count, data)
         
        # Reload our filesystem to wipe away caches
        self.FILE_SYSTEM = pytsk3.FS_Info(self.IMG, self.OFFSET_BYTES, pytsk3.TSK_FS_TYPE_DETECT)


    def _sector_to_block(self, sector):

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


    def lookup_block(self, block):
        """
            Given a block on the filesystem, lookup the file
        """
#        print "lookup: %d" % block
        if block in self.fs_block_to_file:
            f = self.fs_block_to_file[block]
            return f
        else:
            return None


    def _mft_record_to_sectors(self, record_no):
        """
            Given an MFT record number, returns the sectors
            that it occupies.
            
            Assumes that the MFT has been properly parsed!  Relies on record 0 ($MFT)
            being correct.
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
                
                return range(sector_start, sector_start+1024/self.SECTOR_SIZE)
                
            else:
                bytes_left -= num_blocks * self.BLOCK_SIZE
        
        # we only get here if record_no is too high to actually be in the MFT        
        return []

        
    
    def _mft_dataruns(self):
        
        # get inode 0
        mft_f = self.FILE_SYSTEM.open_meta(inode=0)
        
        mft_blocks = []
        for attribute in mft_f:
            if attribute.info.type == pytsk3.TSK_FS_ATTR_TYPE_NTFS_DATA:
                for run in attribute:
                    mft_blocks.append((run.len, run.addr))
                    
        return mft_blocks
        

    def _is_MFT_data(self, data):
        """
        Peeks into start of the data and determines if it contains MFT data
        
        Based on whether MFT header is present
        """
        
        magic_number = struct.unpack("<I", data[:4])[0]
        
        return (magic_number == 0x46494C45 or # FILE
                magic_number == 0x44414142) # BAAD





def main(args=None):

    url = "/home/ch23339/WinXPSP3.img"
    SE = SemanticEngineDisk(url=url)
    print SE.get_access(1256123, 5, 0)


if __name__ == "__main__":
    main()
