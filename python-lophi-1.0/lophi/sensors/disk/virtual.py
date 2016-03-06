"""
    This file contains the class to connect to our VM disk introspection server

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import socket
from time import sleep
import os
import logging
logger = logging.getLogger(__name__)

# LO-PHI
from lophi.sensors.disk import DiskSensor
from lophi.data import DiskSensorPacket
import lophi.globals as G


# Some Globals
VM_HOST = "127.0.0.1"
VM_PORT = 31337
SOCKET_RETRY = 15 # Seconds

VM_HEADER_STRING = 'QIII';

VERBOSE = False


class DiskSensorVirtual(DiskSensor):
    """"
        This class will handle connecting to and communicating with our disk
        introspection server
    """


    def __init__(self, disk_img, host=VM_HOST, port=VM_PORT):
        """ Initialize our class """

        # Set our variables
        self.VM_HOST = host
        self.VM_PORT = port
        self.DISK_IMG = disk_img
        self.SOCK = None
        
        self.name = os.path.basename(disk_img)+"-DiskSensor"

        if disk_img is None:
            logger.error("No disk image filename provided.")
            
        DiskSensor.__init__(self)


    def __exit__(self, t, value, traceback):
        """ Close our socket when the object is destroyed """
        self._disconnect()
        
        
    def _connect(self):
        """
            Connect to our server
        """

        if self.DISK_IMG is None:
            logger.error("No disk image filename provided.")
            return

        # Open our Socket
        self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to our socket
        self._connect_sock()

        # Request introspection from the server (use the defined Xen Disk)
        logger.debug("Sending server request... (%s)"%self.DISK_IMG)
        
        self.SOCK.send("n " + self.DISK_IMG)

        logger.debug("Waiting for data from server...")


    def _disconnect(self):
        """ Close up shop """
        try:
            if self.SOCK is not None:
                self.SOCK.close()
        except:
            pass
        
        self.SOCK = None


    def _read_raw_packet(self,size):
        """
            Read and return raw data from our socket
        """
        recv_data = self.SOCK.recv(size)
        
        logger.debug("Read %d bytes."%len(recv_data))
        return recv_data
        
        
    def get_disk_packet(self):
        """
            Get the next packet header/data
        """
        
        if self.SOCK is None:
            self._connect()
        
        access_packet = DiskSensorPacket()

        # Try forever to get a packet
        while 1:
            # Receive our header
            header = self._read_raw_packet(len(access_packet))

            # Did our socket get closed?
            if len(header) < len(access_packet):
                logger.warn("Introspection server disconnected.")
                # reconnect and try again
                self._connect()
                continue
            
            access_packet = DiskSensorPacket(header)

            # Read for as long as the header tells us to to get the content
            data = ""
            recvd = 0
            while len(data) < access_packet.size:
                logger.debug("Read data.")
                tmp = self.SOCK.recv(access_packet.size - recvd);
                data += tmp
                recvd = len(data)
                if len(tmp) == 0:
                    logger.warn("Introspection server disconnected.")
                    break

            # Did our socket get closed?
            if recvd < access_packet.size:
                logger.warn("Introspection server disconnected.")
                # reconnect and try again
                self._connect()
                continue

            logger.debug("Read %d bytes of data."%len(data))
            
            # Return our data
            access_packet.data = data
            
            return access_packet


    """
        VM Specific Functions
    """


    def _connect_sock(self):
        """
            Simple function to keep trying to connect forever
        """
        while 1:
            try:
                self.SOCK.connect((self.VM_HOST, self.VM_PORT))
                break
            except:
                logger.error("Couldn't connect to host, retrying in %d seconds..." % SOCKET_RETRY)
                sleep(SOCKET_RETRY)
                continue
            
        logger.info("Connected to disk introspection server.")

