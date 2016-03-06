"""
    Some basic network functions

    (c) 2015 Massachusetts Institute of Technology
"""
import socket
import fcntl
import struct
import multiprocessing
import logging
logger = logging.getLogger(__name__)

import lophi.globals as G

UDP_RECV_BUFFER_SIZE = 999999999 #919430400


def get_ip_address(ifname):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915, # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
        return ip
    except:
        return None

def ip2int(addr):                                                               
    return struct.unpack("!I", socket.inet_aton(addr))[0]

def int2ip(buffer):                                                          
    o = str(ord(buffer[0]))
    o += "."
    o += str(ord(buffer[1]))
    o += "."
    o += str(ord(buffer[2]))
    o += "."
    o += str(ord(buffer[3]))
    
    return o



class PacketReaderUDP(multiprocessing.Process):
    """
        This class will listen on a UDP socket and read all 
    """
    def __init__(self,socket,output_queue,packet_type=None,
                 bind_ip=None,
                 bind_port=None,
                 timeout=0):
        """
            Intialize our reader with either an already open socket or an IP/port
            
            @param socket: Socket used for listening
            @param output_queue: Queue used to hand packets back to calling program
            @param packet_type: [Optional] Class that will be initialized with raw data (E.g. LOPHIPacket)
            @param bind_ip: [Optional] IP to bind to if no socket given
            @param bind_port: [Optional] Port to bind to if no socket given
            @param timeout: Timeout for socket.  Will return None if the socket 
            times out  
             
        """
        # Is a socket provided?
        if socket is not None:
            self.SOCK = socket
            self.connected = True
        else:
            self.connected = False
            self.bind_ip = bind_ip
            self.bind_port = bind_port
            
        self.timeout = timeout
            
        self.output_queue = output_queue
        self.packet_type = packet_type
        
        multiprocessing.Process.__init__(self)

    def __del__(self):
        """
            Try to disconnect the socket when the object is deleted.
        """
        logger.debug("Destroying Packet Reader.")
        self.stop()

    def _connect(self):
        """
            Bind to socket
        """

        logger.debug("Connecting to disk sensor")

        # Open socket
        self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Ensure that the socket is reusable
        self.SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    
        # Bind to our port and listening for incoming packets
        self.SOCK.bind((self.bind_ip, self.bind_port))

        # Make our buffer much larger to help prevent packet loss
        self.SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, G.UDP_RECV_BUFFER_SIZE)
        
        
#         if self.timeout > 0:
#             self.SOCK.settimeout(timeout)
        
    def _disconnect(self):
        """ Close up shop """
        
        logger.debug("Disconnecting from Packet Reader (UDP).")
            
        # Should we close our socket, or is another process handling the socket?
        if self.SOCK is not None:
            try:
                self.SOCK.close()
                logger.debug("Socket closed.")
            except:
                logger.error("Could not close socket.")
            self.SOCK = None
        
    def run(self):
        """
            Ensure that we are binded to the socket and listen forever.
        """
        if not self.connected:
            self._connect()
        
        while 1:
            # Read UDP data off the wire
            try:
                recv_data, recv_addr = self.SOCK.recvfrom(G.MAX_PACKET_SIZE)
            except:
                logger.error("Could no receive data from socket.")
                break

            logger.debug("Received packet. (%d bytes)"%len(recv_data))
            
            # Should we conver this packet to an object?
            if self.packet_type is not None:
                try:
                    packet = self.packet_type(recv_data)
                    self.output_queue.put(packet)
                    continue
                except:
                    logger.error("Could not convert raw packet to given packet_type class.")
                    continue
            else:
                self.output_queue.put((recv_data,recv_addr))
                  
    def stop(self):
        """ Kill our process nicely """
        logger.debug("Killing udp reader process...")
        try:
            self._disconnect()
            self.output_queue.close()
        except:
            pass
        self.terminate()