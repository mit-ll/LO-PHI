"""
    Class to handle logging over UDP

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import socket
import logging
logger = logging.getLogger(__name__)

class LogUDP:
    
    
    def __init__(self,address,port):
        """
            Intialize our UDP logger
            
            @param address: Address of remote server
            @param port: port of listening server 
        """
        
        self.address = address
        self.port = port
        
        self.SOCK = None
        self.connected = False
        
        
    def _connect(self):
        """
            Create our socket
        """
        if self.connected:
            return True
        
        try:
            self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.connected = True
            return True
        except:
            logger.error("Could not open UDP socket")
            return False


    def append(self, data):
        """
            Write raw data to the UDP socket
            
            @param data: Data to be written to the UDP socket 
        """
        assert self._connect()
        
        try:
            self.SOCK.sendto(data,(self.address,self.port))
        except:
            logger.error("Could not send UDP packet")