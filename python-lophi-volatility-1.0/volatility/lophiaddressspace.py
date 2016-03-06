"""
    This is the address space to iteract with both physical and virtual machines
    using LO-PHI sensors.

@author:       Chad Spensky, Joshua Hodosh
@contact:      chad.spensky@ll.mit.edu, joshua.hodosh@ll.mit.edu
@organization: MIT Lincoln Laboratory
"""

import sys
import struct
import logging
logger = logging.getLogger(__name__)

import volatility.addrspace as addrspace

try:
    from lophi.sensors.memory.physical import MemorySensorPhysical
    from lophi.sensors.memory.virtual import MemorySensorVirtual
except:
    logger.error("python-lophi does not appear to be installed!")

class LoPhiAddressSpace(addrspace.BaseAddressSpace):
    """Address space for using LO-PHI memory sensor.
     Mediates requests for the contents of a physical address and length
     through the network to a LO-PHI memory device.
     This is selected for locations of type 'lophi://hostname-or-IPv4'"""

    order = 98
    def __init__(self, base, config, layered=False, **kwargs):
        addrspace.BaseAddressSpace.__init__(self, base, config, **kwargs)
        self.as_assert(base == None or layered, 'Must be first address space')
        
        if config.LOPHI_CACHE:
            logger.info("LO-PHI Cache ENABLED.")
            cache_timeout = 1
        else:
            cache_timeout = 0
        
        if config.LOCATION.startswith("lophi://"):
            location = config.LOCATION[8:]
            self.client = MemorySensorPhysical(location,
                                               cache_timeout=cache_timeout)
        elif config.LOCATION.startswith("vmi://"):
            location = config.LOCATION[6:]
            self.client = MemorySensorVirtual(location,
                                              cache_timeout=cache_timeout)
            self.dtb = self.get_cr3()
        else:
            raise("Not a valid LO-PHI URN. (lophi:// for physical and vmi:// for virtual)")
            
        self.fname = location
        self.name = location
        self.cache = False
        self.cache_data = {}
        self.address = 0
        
        
        if config.RAM_SIZE is None:
            print "ERROR/LO-PHI: No RAM size defined. (e.g. --ram_size=12GB)"
            sys.exit(0)

        self.size  = self.parse_byte_amount(config.RAM_SIZE)
        
        self.config = config
        
        self._exclusions = sorted([]) # no info about the HW, nothing to exclude

    def set_cache(self,status):
        """
            Enable/Disable caching
            
        """
        self.cache = status
        
        if status == False:
            self.cache_data = {}

    def read(self, addr, length):
        """
            Read data from memory
            
            @param addr: Address to read from
            @param lengt: Length of data to read
        """
        return self.client.read(addr,length)

    def write(self, addr, data):
        """
            Write data to memory
            
            @param addr: Address to write to
            @param data: Data to write to memory 
        """
        nbytes = self.vmi.write_pa(addr, data)
        if nbytes != len(data):
            return False
        return True


    def get_cr3(self):
        """
            Return cr3 value with virtual sensor only
        """
        if isinstance(self.client,MemorySensorVirtual):
            return self.client.get_vcpureg("cr3", 0);
        else:
            return None


    """
        Unsure what all of these do, but Josh implement them.
        Leaving them to investigate later.
        
    """
    @staticmethod
    def register_options(config):
        config.add_option("RETRIES", type = 'int', default = 5,
              help = "Maximum attempts to retry a timed-out LO-PHI request")

        config.add_option("TIMEOUT", type = 'float', default = 0.5,
              help = "Timeout period for LO-PHI read operations")

        config.add_option("RAM_SIZE", type = 'string',
              help = "Amount of RAM in the target device. This is used to bound scans."
              " Units can be bytes, or KB with 'K' or 'KB' suffix, MB with 'M' or 'MB' "
              "suffix, or GB with 'G' or 'GB' suffix.")
        config.add_option("LOPHI_CACHE", type = 'int', default = False,
                          help="Enable caching for LO-PHI.")
            # There are no kibibytes, mebibytes, or gibibytes in this program.

    @staticmethod
    def parse_byte_amount(spec_string):
        
        if spec_string is None: return None
        
        spec_string = str(spec_string)
        
        normalized = spec_string.lower().strip()
        multiplier = 1
        if normalized.endswith ('kb') or normalized.endswith('k'):
            multiplier = 1024
        elif normalized.endswith('mb') or normalized.endswith('m'):
            multiplier = 1024*1024
        elif normalized.endswith('gb') or normalized.endswith('g'):
            multiplier = 1024*1024*1024
        if normalized[-1] == 'b':
            normalized = normalized[:-2]
        elif not normalized[-1].isdigit():
        #while not normalized[-1].isdigit():
            normalized = normalized[:-1]
        
        return int(normalized) * multiplier

    def intervals(self, start, end):
        return [(start,end)]

    def fread(self,len):
        data = self.read(self.address,len)
        self.address += len
        return data

    
    def zread(self, addr, len):
        return self.read(addr, len)

    def read_long(self, addr):
        string = self.read(addr, 4)
        (longval, ) =  struct.unpack('=L', string)
        return longval

    def get_available_addresses(self):
        yield (0,self.size -1)

    def is_valid_address(self, addr):
        if addr == None:
            return False
        return self.size is None or addr < self.size

    def close(self):
        #self.fhandle.close()
        pass

    def subscribe(self, startaddr, endaddr, data, threadclass):
        return self.client.subscribe_api(startaddr, endaddr, data, threadclass)
