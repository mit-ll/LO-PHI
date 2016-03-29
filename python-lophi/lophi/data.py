"""
    Class for easily handling C-style structs in Python

    (c) 2015 Massachusetts Institute of Technology
"""
import struct
import logging
logger = logging.getLogger(__name__)

import globals as G

class DataStruct:
    """
        This is an abstract class used to define structures in memory in an easy
        way.
        
        STRUCT is the only variables one needs to set
        
        Ref: http://docs.python.org/2/library/struct.html
        
        Example:
        
        class Test(DataStruct):
            STRUCT = [('byte1','B'), 
                      ('byte2','B')]
    """
    STRUCT = None

    def __init__(self, data=None, name=None):
        """
            Initialize our representation of a struct
            
            @param data: If given will parse data
            @param name: Just a way to keep track of instances
        """
        # General error checks
        if self.__class__ == DataStruct:
            raise("This is an abstract class and should not be initialized directly")
        
        if self.STRUCT is None:
            logger.error("You must specifiy STRUCT and NAMES for MemoryStructs.")
            return
        
        # Store variables for later
        if name is not None:
            self.struct_name = name
        else:
            self.struct_name = self.__class__.__name__
        
        self.data = None
        
        # Check to see if we have any violations that will overwrite existing variables
        for n in self.STRUCT:
            if n in self.__dict__.keys():
                logger.error("%s cannot be used a variable name."%n)
                return
        
        # Initialize all of our variables
        self.STRUCT_SIZE = 0
        for (key,fmt) in self.STRUCT:
            self.__dict__[key] = None
            
            # Set our structure size
            self.STRUCT_SIZE += struct.calcsize(fmt)
        
        # Was data provided to parse?
        if data is not None:
            self._unpack(data)
        else:
            self.struct_raw_data = "\x00"*self.STRUCT_SIZE

    def __setattr__(self,key,value):
        """
            Set our attributes, if its an attribute of the struct, update our
            buffer representation
        """
        tmp = None
        if key in self.__dict__:
            tmp = self.__dict__[key]
            
        # Update our new value
        self.__dict__[key] = value
        
        # If its one of the keys in our struct, update our raw buffer
        # Todo put the pack function here inline
        success = True
        for (key2,fmt) in self.STRUCT:
            if key == key2:
                success = (success and self._pack())
                
        if not success:
            self.__dict__[key] = tmp
        
    def __getitem__(self,index):
        """
            Return a specific byte from our raw data
            
            @param index: Index into raw data buffer to return 
        """
        if self.struct_raw_data is not None and index > len(self.struct_raw_data):
            return self.struct_raw_data[index]
        
    def __iter__(self):
        """
            Return an interator through the bytes in the raw data
        """
        return iter(self.struct_raw_data)
        
    def __len__(self):
        """
            Return the length of the structure in memory
        """
        if self.data is None:
            return self.STRUCT_SIZE
        else:
            return self.STRUCT_SIZE + len(self.data)
    
    def __eq__(self, comp):
        """
            Compare our memory structure to a raw memory buffer and see if they are equal
        """
        
        if len(comp) != len(self):
            logger.debug("Tried to compare a buffer of different size.")
            return False
        
        offset = 0
        for (key,fmt) in self.STRUCT:
            value = self.__dict__[key]
            size = struct.calcsize(fmt)
            
            if value is not None:
                if self.struct_raw_data[offset:size] != comp[offset:size]:
                    return False
                
            offset += size
        
        return True
    
    def __repr__(self):
        """
            Return the raw packed buffer w/ data
        """
        if self.data is None:
            return self.struct_raw_data
        else:
            return self.struct_raw_data + self.data
    
    def __str__(self):
        """
            Print output in human readable format
        """
        o = "[%s]\n"%self.struct_name
        for (key,fmt) in self.STRUCT:
            o += "  %s: %s\n"%(key,self.__dict__[key])
            
        if self.data is not None:
            o += "  Data: [%d bytes]\n"%len(self.data)
        
        # Trim trailing \n
        return o[:-1]
    
    def _unpack(self,data):
        """
            Unpack the raw data into semantic meaning
            
            @param data: raw binary data to extract into our struct format
        """
        
        # See if enough data was provided
        if len(data) < self.STRUCT_SIZE:
            logger.error("Data provided to struct is < %d bytes. (%d bytes)"%(
                                                            self.STRUCT_SIZE,
                                                            len(data)))
            return
        
        # Do we have data after our structure?
        elif len(data) > self.STRUCT_SIZE:
            self.data = data[self.STRUCT_SIZE:]
            
        self.struct_raw_data = data[:self.STRUCT_SIZE]
    
        # Set our values, these will be of the form MemoryStruct.name
        offset = 0
        for (key,fmt) in self.STRUCT:

            v = struct.unpack_from(fmt, self.struct_raw_data, offset)
            if len(v) == 1:
                self.__dict__[key] = v[0]
            else:
                self.__dict__[key] = v
            
            offset += struct.calcsize(fmt)
        
    def _pack(self):
        """
            Pack our struct back into raw data
        """
        
        self.struct_raw_data = ""
        
        for (key,fmt) in self.STRUCT:
                        
            value = self.__dict__[key]
            size = struct.calcsize(fmt)
            
            if type(value) is list or type(value) is tuple:
                if len(value) != size:
                    logger.error("%s was too small, cannot store in this struct. (%d vs %d)"%(key,))
                    return False
                self.struct_raw_data += struct.pack(fmt, *value)
                    
            elif value is not None:
                self.struct_raw_data += struct.pack(fmt, value)
            else:
                self.struct_raw_data += "\x00"*size
        
        return True
    
    def keys(self):
        """
            Return the keys into our structures
        """
        # Loop through our defined list and add the keys
        key_list = []
        for (k, v) in self.STRUCT:
            key_list.append(k)
            
        return key_list

    def values(self):
        """
            Return the values of our structures
        """
        # Loop through our defined list and append the values
        value_list = []
        for (k, v) in self.STRUCT:
            if k in self.__dict__ and self.__dict__[k] is not None:
                value_list.append(self.__dict__[k])
            else:
                value_list.append("")
            
        return value_list
    
    
class DiskSensorPacket(DataStruct):
    """
        This is how data is to be returned from our disk sensors. and fed 
        as input to any of our analysis.
    """
    name = "DiskSensorPacket"
    STRUCT = [('sector','Q'), 
              ('num_sectors','I'),
              ('disk_operation','I'),
              ('size','I')]


class MemorySensorPacket(DataStruct):
    """
        This is the header format for data returned from our memory sensors
        
        address: Physical address of memory
        length: Length of memory region captured in bytes
    """
    name = "MemorySensorPacket"
    STRUCT = [('name','25s'),
              ('address','Q'),
              ('length','I')]


class MemoryRapidPacket(DataStruct):
    """
        This defines the header used by then RAPID protocol, which is abused
        by our memory sensors.
    """
    name = "RAPIDPacket"
    STRUCT = [('MAGIC_LOPHI','!I'),
              ('address_high','!I'), 
              ('operation','!I'), 
              ('address_low','!I'), 
              ('length','!I'), 
              ('flags','!I'),
              ('transaction_no','!I')]


class LOPHIPacket(DataStruct):
    name = "LOPHIPacket"
    STRUCT = [('MAGIC','!I'),
               ('RESERVED','!B'),
               ('op_code','!B'),
               ('memory_addr','!H'),
               ('memory_len','!H'),
               ('frame_len','!H')]


class SATAFrame(DataStruct):
    name = "SATAFrame"
    STRUCT = [('seqn_num','!H'),
              ('direction','!H')]
    
    
class KvmMemRequest(DataStruct):
    """
        Request structure used by libvmi
        
        type - 0 quit, 1 read, 2 write
        address - address to read from OR write to
        length - number of bytes to read/write
    """
    name = "KvmMemRequest"
    STRUCT = [('type','Q'), # Actually B, but it word aligns in C structs... 
              ('address','Q'),
              ('length','Q')]