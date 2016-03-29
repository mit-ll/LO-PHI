"""
    Classes for reading and writing pcap files

    (c) 2015 Massachusetts Institute of Technology
"""
import multiprocessing
import logging
logger = logging.getLogger(__name__)

import dpkt

class PcapWriter(multiprocessing.Process):
    """
        Very simple class to create a pcap file from a network stream
    """
    def __init__(self, filename, input_queue, link_type=dpkt.pcap.DLT_EN10MB):
        """
            Initialize our pcap writer
        """
        
        self.filename = filename
        
        self.input_queue = input_queue
        
        self.pcap_writer = None
        
        # Set our pcap settings
        self.snaplen = 0 # unlimited length
        self.linktype = link_type
        
        # Keep track of running status
        self.EXIT = multiprocessing.Event()
        
        multiprocessing.Process.__init__(self)
        
    def __del__(self):
        """
            Try to close our file nicely
        """
        logger.debug("Destroying PCAP Writer.")
        if self.pcap_writer is not None:
            try:
                self.pcap_writer.close()
            except:
                pass
        
    def run(self):
        """
            Read from our queue and write to a file
        """
        
        try:
            f = open(self.filename, "w+")
        except:
            logger.error("Could not create file. (%s)"%self.filename)
            return
        
        self.pcap_writer = dpkt.pcap.Writer(f, 
                                            snaplen=self.snaplen, 
                                            linktype=self.linktype)
        while not self.EXIT.is_set():
            # Get our packet from the queue
            try:
                (ts,packet) = self.input_queue.get()
            except:
                import traceback
                traceback.print_exc()
                logger.debug("Input queue closed.")
                break
            
            logger.debug("Writing packet to file. (%d bytes)"%len(packet))
            # Write the packet to our pcap file
            self.pcap_writer.writepkt(packet,ts=ts)
            
            # Flush the file buffer in case we die
            f.flush()
            
        self.pcap_writer.close()
            
            
    def stop(self):
        """ Kill our process nicely """
        logger.debug("Killing PcapWriter...")
        self.input_queue.close()
        self.EXIT.set()
        self.terminate()


class PcapReader():
    """
        Very simple class to create a pcap file from a network stream
    """
    def __init__(self, filename, link_type=dpkt.pcap.DLT_EN10MB):
        """
            Initialize our pcap writer
        """
        
        self.filename = filename
        
        self.pcap_reader = None
        
        try:
            f = open(self.filename, "r")
        except:
            logger.error("Could not open %s"%filename)
            return
        
        self.pcap_reader = dpkt.pcap.Reader(f)
        
        
    def __iter__(self):
        """
            Overload dpkt to allow this class to be iterated over.
        """
        if self.pcap_reader is None:
            return None
        else:
            return self.pcap_reader.__iter__()
        
#     def read(self):
#         """
#             Read the next entry from our pcap file
#         """
#         
#         if self.pcap_reader is None:
#             return None
#         else:
#             return self.__iter__()
            
            
    def close(self):
        """ Kill our process nicely """
        self.pcap_reader.close()
        