"""
    Class for interacting with our physical disk sensor (FPGA)

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import socket
import struct
import logging
logger = logging.getLogger(__name__)
import heapq
import multiprocessing
import math


# LO-PHI
import lophi.globals as G
from lophi.sensors.disk import DiskSensor
from lophi.data import SATAFrame
from lophi.data import LOPHIPacket
from lophi.network import PacketReaderUDP
from lophi.data import SATAFrame
import lophi.network as NET


UDP_RECV_BUFFER_SIZE = 0x7fffffff
                       
READ_TIMEOUT = 60
MAX_HEAP_SIZE = 20


class DiskSensorPhysical(DiskSensor):
    """"
        This is an abstract class to help manage both physical and Xen
        implementations.  This will also allow us to expand to new 
        implementations very easily.
    """

    def __init__(self, sensor_ip, 
                 sensor_port=G.SENSOR_DISK.DEFAULT_PORT,
                 bind_ip="0.0.0.0",
                 bind_port = G.SENSOR_DISK.DEFAULT_PORT,
                 sector_size=G.SENSOR_DISK.DEFAULT_SECTOR_SIZE,
                 name=None,
                 use_threading=True):
        """ Initialize our sensor """

        # Set our variables
        self.sensor_ip = sensor_ip
        self.sensor_port = sensor_port
       
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        
        self.sector_size = sector_size
        
        # Keep our connected state
        self.connected = False
        self.sata_enabled = False
        
        # Initialize a heap to re-order SATA frames that arrive out of order
        self.sata_heap = []
        self.last_lophi_seqn = None
        self.last_lophi_packet = None
                
        if name is not None:
            self.name = name
        
        # Are we reading a separate process?
        self.use_threading = use_threading
        self.read_queue = None
        self.packet_reader = None
        
        self.SOCK = None
        
        self.DROPPED_PACKETS = 0
        
        # Connect to the socket
#         self._connect()
        
        DiskSensor.__init__(self)
        
        logger.debug("Initialized Disk Sensor. (%s)"%self.name)
        
        
    def __del__(self):
        logger.debug("Destroying Disk Sensor / Disconnecting. (%s)"%self.name)
        try:
            self._disconnect()
        except:
            pass


    def _connect(self):
        """
            Connect to our sensor
            
            @param enable_sata: Will send the appropriate command to enable SATA
            extraction
        """

        

        if not self.connected:
            logger.debug("Connecting to disk sensor")
            
            try:
                # Open socket
                self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
                # Ensure that the socket is reusable
                self.SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
                # Bind to our port and listening for incoming packets
                self.SOCK.bind((self.bind_ip, self.bind_port))
        
                # Make our buffer much larger to help prevent packet loss
                self.SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, G.UDP_RECV_BUFFER_SIZE)
                
                
                if self.use_threading:
                    logger.debug("Starting listener thread.")
                    # Start a process that will handle all of our reads
                    self.read_queue = multiprocessing.Queue()
                    self.packet_reader = PacketReaderUDP(self.SOCK,self.read_queue)
                    self.packet_reader.start()
            
                self.connected = True
                
                return True
                
            except:
                logger.error("Could not connect to disk sensor")
                return False
        
        return True

#         # Set a timeout
#         self.SOCK.settimeout(READ_TIMEOUT)
        
        # Send our "Wake Up" Packets
#         if self.sata_enable_mode:
#             self.sata_enable_all()
            
        


    def _disconnect(self):
        """ Close up shop """
        
        logger.debug("Disconnecting from disk sensor.")
        
        self.connected = False
        
        # Close our socket
        if self.SOCK is not None:
            logger.debug("Closing socket.")
            self.SOCK.close()
            self.SOCK = None
            
 
        
        # Are we using a threaded reader?         
        if self.packet_reader is not None:
            logger.debug("Killing packet reader thread.")
            try:
                logger.debug("Trying to kill reader thread.")
                self.packet_reader.stop()
                self.packet_reader = None
                logger.debug("Reader thread killed.")
            except:
                G.print_traceback()
                pass
            
        # Close our threaded process for reading?
        if self.read_queue is not None:
            logger.debug("Closing queue.")
            self.read_queue.close()  

        
        
        
    def _send_command(self, operation, memory_address, data=None):
        """
            This is used to interface with the card
        """
        
        if not self._connect():
            return False
        
        # Get our network packet
        packet = LOPHIPacket()

        # Set our agruments
        packet.MAGIC = G.SENSOR_DISK.MAGIC_LOPHI
        packet.op_code = operation
        packet.memory_addr = memory_address
        packet.memory_len = math.ceil(len(data) / 4)
        packet.frame_length = 3 + packet.memory_len # 3 word header + data
        packet.data = data

        raw_data = repr(packet)

        logger.debug("Sending: %s" % repr(packet))
        # Send it across the wire
        self.SOCK.sendto(raw_data, (self.sensor_ip, self.sensor_port))
        
        # Get our response
        lophi_packet = self.get_lophi_packet()
        logger.debug("Response: %s"%str(lophi_packet))
        
        return lophi_packet


    def _read_raw_packet(self,size=G.MAX_PACKET_SIZE):
        """ 
            Read and return raw data from our socket
            
            @return: (data, address) 
        """
        
        if not self._connect():
            return False
            
        # Read UDP data from thread or off the wire
        if self.read_queue is not None:
            recv_data, recv_addr = self.read_queue.get()
        else:
            recv_data, recv_addr = self.SOCK.recvfrom(size)

        logger.debug("Read %d bytes."%len(recv_data))
        return recv_data, recv_addr


    def _get_sata_packet(self):
        """
            This segment of code makes sure that we read our SATA packets in 
            order in case they are re-ordered by the network.
            
            @return: LOPHI SATA packet guaranteed to be in the order sent by sensor.
            @todo: Handle packet loss
        """
        # Make sure SATA extraction is enabled
        if not self.sata_enabled:
            self.sata_enable_all()
        
        lophi_packet = None
        
        while 1:
            # Are we dealing with the heap?
            if len(self.sata_heap) > 0:
                logger.debug("pulling from heap")
                
                heap_next_seqn = self.sata_heap[0][0]
                if heap_next_seqn == (self.last_lophi_seqn+1)%65536 or len(self.sata_heap) > MAX_HEAP_SIZE:
                    
                    if len(self.sata_heap) > MAX_HEAP_SIZE:
                        self.DROPPED_PACKETS += 1
                        logger.warning("Sensor dropped packets. (Data may be unreliable)")
                    lophi_seqn, lophi_packet = heapq.heappop(self.sata_heap)
                    # hack to make sure we don't put it back on the heap
                    self.last_lophi_seqn = lophi_seqn
                    self.last_lophi_packet = lophi_packet
                    
                    # Return our packet
                    return lophi_packet
                
                else:
                    lophi_packet = self.get_lophi_packet()
            else:
                # Get the next packet from the wire
                lophi_packet = self.get_lophi_packet()
            
            # Check the packet from the wire and see if it has the seqn we expected
            if lophi_packet.op_code == G.SENSOR_DISK.OP.SATA_FRAME:
                
                # Extract our SATA data
                sata_frame = SATAFrame(lophi_packet.data)
                
                # Get our sequence number
                lophi_seqn = sata_frame.seqn_num
                
                # Take care of our ordering
                if self.last_lophi_seqn is not None:
                    # If this is an out of order packet, push to heap
                    if lophi_seqn != (self.last_lophi_seqn+1)%65536:
                        heapq.heappush(self.sata_heap,(lophi_seqn,lophi_packet))
                        logger.debug("Got out of order packet. (Expected: %d, Got: %d)"%(
                                                (self.last_lophi_seqn+1)%65536,
                                                lophi_seqn))
                        continue
                
                # Save our last seqn
                self.last_lophi_seqn = lophi_seqn
                self.last_lophi_packet = lophi_packet
                
                # Return our packet
                return sata_frame
                
            else:
                continue
    
    def is_up(self):
        """
            Check to see if the card is up
            
            @return: True/False
        """
        try:
            # Open socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
            # connect to our port+1 which is a UDP loopback
            addr = (self.sensor_ip, self.bind_port+1)
            sock.connect(addr)
            
            # Set a timeout
            sock.settimeout(READ_TIMEOUT)
        
            # Try to send a packet to the UDP loopback
            sock.send("PING")
            
            # Ensure we got the same data back
            rtn = sock.recv(1024)
            if rtn == "PING":
                return True
            
            sock.close()
        except:
            pass
        
        # If anything goes wrong, the card isn't there.
        return False
    
    
    def get_disk_packet(self):
        """
            For now just return the SATA frame, we'll deal with this later.
        """
        logger.debug("Reading disk packet (SATA Frame in this case)...")
        return self._get_sata_packet()

    
    def get_lophi_packet(self):
        """
            Get the next packet header/data
            
            @return: LO-PHI packet as a dictionary 
                - lophi_header: LO-PHI defined header
                - lophi_data:                       
        """
        # Read data off the wire
        logger.debug("Reading LO-PHI packet...")
        recv_data, recv_addr = self._read_raw_packet()

        network_packet = LOPHIPacket(recv_data)

#         logger.info("Received: %s"%network_packet)        
        return network_packet

    
    """
        Physical Specific Functions
    """


    def get_version(self):
        """
            Returns the current version of the sensor
            
            @return: Version of sensor retrieved from card
        """
        self._send_command(G.SENSOR_DISK.OP.REG_READ, G.SENSOR_DISK.ADDR.VERSION)
        packet = self.get_lophi_packet()
        version = packet.data
        return version

    def sata_enable_host(self):
        """
            Enable host only SATA extraction
        """
        logger.debug("Sending packet to enable sata extraction.")
        self._send_command(G.SENSOR_DISK.OP.REG_WRITE, 
                           G.SENSOR_DISK.ADDR.SATA_CTRL,
                            "\x00\x00\x00\x01")

    def sata_enable_device(self):
        """
            Enable device only SATA extraction
        """
        logger.debug("Sending packet to enable sata extraction.")
        self._send_command(G.SENSOR_DISK.OP.REG_WRITE, 
                           G.SENSOR_DISK.ADDR.SATA_CTRL,
                            "\x00\x00\x00\x02")

    def sata_enable_all(self):
        """
            Enable bi-directional SATA extraction
        """
        logger.debug("Sending packet to enable sata extraction.")
        self._send_command(G.SENSOR_DISK.OP.REG_WRITE,
                           G.SENSOR_DISK.ADDR.SATA_CTRL,
                           "\x00\x00\x00\x03")
        self.sata_enabled = True

    def sata_disable(self):
        """
            Disable SATA extraction
        """
        logger.debug("Sending packet to disable sata extraction.")
        self._send_command(G.SENSOR_DISK.OP.REG_WRITE,
                           G.SENSOR_DISK.ADDR.SATA_CTRL,
                           "\x00\x00\x00\x00")
        self.sata_enabled = False
        return True

    def print_all_registers(self):
        
        
        registers = self.get_all_registers()

        for (reg, addr, data) in registers:
            data_list = struct.unpack("%dB" % len(data), data)
                
            data_list2 = " ".join([hex(i) for i in data_list])
            
            print "%s (%s): %s / %s"%(reg,hex(addr),data_list2,data_list)
            

    def get_all_registers(self):
        """
            Returns all of the registers on the sensor
            
            @return: list of tuples (name, address, value)
        """
        logger.debug("Requesting all registers")
        
        
        
        registers = []
        for reg in G.SENSOR_DISK.ADDR.__dict__: # @UndefinedVariable
            if reg.startswith("_"):
                continue
            
            addr = G.SENSOR_DISK.ADDR.__dict__[reg] # @UndefinedVariable
            
            lophi_packet = self._send_command(G.SENSOR_DISK.OP.REG_READ, addr, "",1)
            
            data = lophi_packet.data
            
            registers.append((reg,addr,data))
            
        return [x for x in registers if x is not None] 
        
        

    def set_dest_ip(self,dest_ip):
        """
            Set the destination IP for our SATA frames
            
            @param dest_ip: Destination IP that SATA packets will be sent to 
        """
        
        logger.debug("Setting destination IP to %s."%dest_ip)
        
        ip = struct.pack('>I',NET.ip2int(dest_ip))
        
        lophi_packet = self._send_command(G.SENSOR_DISK.OP.REG_WRITE, 
                                          G.SENSOR_DISK.ADDR.IP_DEST, 
                                          ip)
        
        if lophi_packet.header['op_code'] == G.SENSOR_DISK.OP.REG_WRITE and lophi_packet.header['memory_addr'] ==  G.SENSOR_DISK.ADDR.IP_DEST:
            return True
        else:
            return False
        
        
    def set_sensor_ip(self,ip):
        """
            Set the card IP address
            
            @param ip: IP address of this sensor 
        """
        
        logger.debug("Setting sensor IP to %s."%ip)
        
        ip = struct.pack('>I',NET.ip2int(ip))
        
        lophi_packet = self._send_command(G.SENSOR_DISK.OP.REG_WRITE, 
                                          G.SENSOR_DISK.ADDR.IP_SENS, 
                                          ip)
        
        if lophi_packet.header['op_code'] == G.SENSOR_DISK.OP.REG_WRITE and lophi_packet.header['memory_addr'] ==  G.SENSOR_DISK.ADDR.IP_SENS:
            return True
        else:
            return False

        
    def set_udp_delay(self,delay):
        """
            Set the intrapacket delay for UDP packets
            
            @param delay: Delay in clock cycles (~10ns/cycle) between packets
        """
        
        logger.debug("Setting UDP intrapacket delay to: %s"%delay)
        
        delay = struct.pack('>I',delay)
        
        lophi_packet = self._send_command(G.SENSOR_DISK.OP.REG_WRITE, 
                                          G.SENSOR_DISK.ADDR.UDP_DELAY,
                                          delay)
        
        if lophi_packet.header['op_code'] == G.SENSOR_DISK.OP.REG_WRITE and lophi_packet.header['memory_addr'] ==  G.SENSOR_DISK.ADDR.UDP_DELAY:
            return True
        else:
            return False
        
        
    def set_mtu_size(self,mtu_size):
        """
            Set the MTU size for UDP packets
            
            @param mtu_size: Maximum transfer unit size for UDP packets in bytes
        """
        
        logger.debug("Setting MTU for packets to: %s"%mtu_size)
        
        mtu_size = struct.pack('>I',mtu_size)
        
        lophi_packet = self._send_command(G.SENSOR_DISK.OP.REG_WRITE, 
                                          G.SENSOR_DISK.ADDR.MTU_SIZE,
                                          mtu_size)
        
        if lophi_packet.header['op_code'] == G.SENSOR_DISK.OP.REG_WRITE and lophi_packet.header['memory_addr'] ==  G.SENSOR_DISK.ADDR.MTU_SIZE:
            return True
        else:
            return False
        