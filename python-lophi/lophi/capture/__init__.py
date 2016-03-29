"""
    Classes for capturing raw data

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import multiprocessing
import logging
import time
import struct
logger = logging.getLogger(__name__)

# LO-PHI
from lophi.data import DataStruct

class CapHeader(DataStruct):
    """
        This is the header format for our Disk Capture format
        
        timestamp: Time packet was observed
        length: Length of data captured
    """
    STRUCT = [('timestamp','>f'), 
              ('length','>I')]


class CaptureHandler:
    f = None
    
    def __del__(self):
        """
            Try to close our file nicely
        """
        try:
            self.f.close()
        except:
            pass

    def _open(self, perm="r"):
        """
            Open our input file
            
            @param perm: open permissions
        """
        try:
            self.f = open(self.filename, perm)
            return True
        except:
            logger.error("Could not open file with '%s' perms. (%s)"%(perm,
                                                            self.filename))
            return False
        
    def read(self, size):
        """
            Read size bytes from our file descriptor
        """
        return self.f.read(size)
    
    def write(self,data):
        """
            Write data to our file descriptor
        """
        rtn = self.f.write(data)
        self.f.flush()
        return rtn
    
       
class CaptureWriter(CaptureHandler, multiprocessing.Process):
    """
        Main class for writing captures to file
    """
    def __init__(self, filename, input_queue=None):
        """
            Initialize our disk capture writer
        """
        
        self.filename = filename
        
        if input_queue is None:
            self.input_queue = multiprocessing.Queue()
        else:
            self.input_queue = input_queue
        
        # Keep track of running status
        self.EXIT = multiprocessing.Event()
        
        multiprocessing.Process.__init__(self)

    def put(self,data):
        """
            Put something on the queue
        """
        self.input_queue.put(data)
        
    def run(self):
        """
            Read from our queue and write to a file
        """
        
        logger.debug("Starting Capture Writer...")
        # Ensure our file is open
        if self.f is None and not self._open("w+"):
            return None
        
        # Declare our header
        cap_header = CapHeader()
        
        # Write forever
        while not self.EXIT.is_set():
            # Get our packet from the queue
            try:
                packet = self.input_queue.get()
            except:
                logger.debug("Input queue closed.")
                break
            
            logger.debug("Writing packet to file. (%d bytes)"%len(packet))
            
            # Set our header values
            cap_header.timestamp = time.time()
            cap_header.length = len(packet)
            
            # Write the packet to our pcap file
            self.write(`cap_header`)
            if type(packet) == 'str':
                self.write(packet)
            else:
                self.write(`packet`)
                
        self.f.close()
        
    def stop(self):
        """ Kill our process nicely """
        logger.debug("Stopping CaptureWriter...")
        
        try:
            self.input_queue.close()
            self.EXIT.set()
            self.terminate()
        except:
            pass
        

class CaptureReader(CaptureHandler):
    """
        Main class for reading captures from file
    """

    def __init__(self,filename):
        """
            Initialize our reader
        """
        self.filename = filename
        
    def __iter__(self):
        
        return self
    
    def next(self):
        """
            Read from our queue and write to a file
        """
        # Ensure our file is open
        if self.f is None and not self._open():
            raise StopIteration

        #print "pos", self.f.tell()
        # Declare our header
        cap_header = CapHeader()

        # Read header from file
        logger.debug("Reading header. (%d bytes)"%len(cap_header))
        header_data = self.read(len(cap_header))
        if len(header_data) == 0:
            logger.debug("Hit end of file.")
            raise StopIteration
        cap_header._unpack(header_data)
        
        # Read data from file
        logger.debug("Reading data. (%d bytes)"%cap_header.length)
        packet_data = self.read(cap_header.length)
        
        return (cap_header.timestamp, packet_data)

    def tail(self):
        """
            Only report new data data in the cap file as a generator
            
        """
        
        # Ensure our file is open
        if self.f is None and not self._open():
            raise StopIteration
        
        while True:
            # Declare our header
            cap_header = CapHeader()
            # Read header from file
            logger.debug("Reading header. (%d bytes)"%len(cap_header))
            header_data = self.read(len(cap_header))
            
            if len(header_data) == 0:
                logger.debug("No data left in file.")
                time.sleep(1)
                continue
            
            cap_header._unpack(header_data)
            
            # Read data from file
            logger.debug("Reading data. (%d bytes)"%cap_header.length)
            packet_data = self.read(cap_header.length)
            
            if len(packet_data) == 0:
                logger.debug("No data left in file.")
                time.sleep(.01)
                continue
            
            yield (cap_header.timestamp, packet_data)
    

class CaptureReaderTail(CaptureHandler):
    """
        Main class for reading captures from file but with tail -f like behavior.
        It is not iterable.
    """

    def __init__(self,filename):
        """
            Initialize our reader
        """
        self.filename = filename
        
        # current position in file
        self.where = 0

    def __iter__(self):
        """ This class is its own iterator """
        return self
    
    def next(self):
        """
            Read from the file and return data
        """
        # Ensure our file is open
        if self.f is None and not self._open():
            raise Exception("CaptureReaderTail: file is not open!")

        # seek to the correct place
        self.f.seek(self.where)

        # list of (timestamp, packet_data) pairs to return
        ret = []

        # read and parse until we hit the end of the file
        while True:
            #print "pos", self.f.tell()
        
            # Declare our header
            cap_header = CapHeader()

            # Read header from file
            logger.debug("Reading header. (%d bytes)"%len(cap_header))
            header_data = self.read(len(cap_header))
        
            # check length of the header based on the struct format
            # TODO do this automatically
            if len(header_data) < struct.calcsize('fI'):
                # hit end of file
                break
        
            cap_header._unpack(header_data)
        
            # Read data from file
            logger.debug("Reading data. (%d bytes)"%cap_header.length)
            packet_data = self.read(cap_header.length)
            
            if len(packet_data) < cap_header.length:
                # hit end of the file, we need to wait
                # until this packet is completely written
                break
        
            # append the result
            ret.append((cap_header.timestamp, packet_data))

            # update our current position where we are leaving off            
            self.where = self.f.tell()
    
        return ret