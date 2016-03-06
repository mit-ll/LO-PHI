"""
    Class for interacting with our physical memory sensor (FPGA)

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import socket
import time
import logging
logger = logging.getLogger(__name__)

import multiprocessing

# LO-PHI
import lophi.globals as G
from lophi.sensors.memory import MemorySensor
from lophi.data import MemoryRapidPacket
from lophi.network import PacketReaderUDP

network_lock = multiprocessing.Lock()


MAX_THREAD_READ = 7680*10 # Unimplemented... but should it be?
READ_CHUNK = 7680

class MemorySensorPhysical(MemorySensor):
    """
        This is our interface to both our NetFPGA and ML507 boards using Josh's
        code.
    """
    
    
    def __init__(self, sensor_ip=G.SENSOR_MEMORY.DEFAULT_IP, 
                sensor_port=G.SENSOR_MEMORY.DEFAULT_PORT,  
                 cache_timeout=0, 
                 name=None,
                 use_threading=False,
                 timeout=1,
                 retries=5):
        """
            Initialize our memory sensor.  Just saving values at this point.
    
            @param cache_timeout: How long to keep data in the cache (seconds)
            @param name: Human name of the sensor
            @param use_threading: This will spawn a new process to read replys 
            from the sensor.  Enables much faster reads, but will eventually 
            blow the UDP stack in the FPGA. 
        """
        # Sensor info
        self.sensor_ip = sensor_ip
        self.sensor_port = sensor_port
        
        # Socket variables
        self._sock = None
        self.TIMEOUT = timeout
        self.RETRIES = retries
        self.TIMED_OUT = False
        self.connect_count = 0
        
        # Are we reading a separate process?
        self.use_threading = use_threading
        self.read_queue = None
        self.packet_reader = None
        
        # Cache
        self.cache = {}
        self.cache_timeouts = {}
        self.CACHE_TIMEOUT = cache_timeout # seconds
        
        # Keep track of our transaction
        self.transaction_no = 1
        
        if name is not None:
            self.name = name
            
        # Bad read regions (On XPSP3x86)
        # Ref: http://wiki.osdev.org/Memory_Map_%28x86%29
        self.BAD_MEM_REGIONS = [(0xA0000, 0x100000), # VGA and PCI
                                (0x7fe00000,0x80000000), # No Clue
                                (0xdbf00000,0x100000000), # High Mem PCI devices
                                (0x3ff00000,0x40000000) # No clue (End of memory?
                                ]
        
        # Initialize our superclass as well
        MemorySensor.__init__(self)
        
        
    def __del__(self):
        """
            Clean up any connections when the object is destroyed
        """
        self._disconnect()
        
        
    def _connect(self):
        """
            Connect our socket. 
        """
        # Is the socket already open?
        if self._sock is None:
            # Open our socket
            try:
                logger.debug("Connecting to memory sensor. ")
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 100000)
                s.connect((self.sensor_ip, self.sensor_port))
                
#                 if self.timeout is not None:
#                     s.settimeout(self.timeout)
    
                if self.use_threading:
                    logger.debug("Starting listener thread.")
                    # Start a process that will handle all of our reads
                    self.read_queue = multiprocessing.Queue()
                    self.packet_reader = PacketReaderUDP(s,self.read_queue)
                    self.packet_reader.start()
                elif self.TIMEOUT is not None and self.TIMEOUT > 0 :
                    s.settimeout(self.TIMEOUT)
                    
                
            except:
                logger.error("Could not connect to memory sensor. (%s,%d)"%(self.sensor_ip,self.sensor_port))
                self.connect_count += 1
                
                if self.connect_count > self.RETRIES:
                    raise socket.error("Could not connect to memory sensor.")
                
                return False
            
            
            # Save our socket
            self._sock = s

        return True
        self.connect_count = 0
    
    
    def _disconnect(self):
        """
            Disconnect our socket.
        """
        if self._sock is not None:
            self._sock.close()
            self._sock = None
            
        if self.read_queue is not None:
            self.read_queue.close()
            self.read_queue = None
            
        if self.packet_reader is not None:
            self.packet_reader.terminate()
            self.packet_reader = None
    
    
    def _send_command(self,command,address,length, data=None):
        """
            Send a command to to the card
            
            @param command: LO-PHI command to send
            @param address: Address on the SUT (Not address on the FPGA)
            @param length: Length for the command (Not the length of the packet)
            @param data: Any data to append to the packet 
        """
        
        logger.debug("Sending command (0x%x, 0x%x, %d)"%(command,address,length))
   
        # Build our payload
        packet = MemoryRapidPacket()
        
        # Constants
        packet.MAGIC_LOPHI = G.SENSOR_MEMORY.MAGIC_LOPHI
        packet.flags = G.SENSOR_MEMORY.DEFAULT_FLAGS
        
        # Command
        packet.operation = command
        
        # Split our address
        lowaddress = (address) & 0xFFFFFFFF
        highaddress = address >> 32
        packet.address_high = highaddress
        packet.address_low = lowaddress
        
        # Data
        packet.length = length
        packet.data = data
        
        # Transcation num
        packet.transaction_no = self.transaction_no
        
        # Increment our transcation number
        self.transaction_no = (self.transaction_no+1)%0x0000ffff
                
        # Keep trying to reconnect
        while not self._connect():
            time.sleep(1)
        
        # Send payload to our sensor
        sent = self._sock.send(`packet`)
        if sent != len(packet):
            logger.error("Only sent {0} out of {1}".format(sent, len(packet)))
            dead = True
            
    
    
    def _read_raw_packet(self,size=G.MAX_PACKET_SIZE):
        """ 
            Read and return raw data from our socket
            
            @return: (data, address) 
        """
        
        # If we already timed out, assume the sensor is dead
        if self.TIMED_OUT:
            raise socket.timeout
        
        # Keep trying to reconnect
        while not self._connect():
            time.sleep(1)
            
        # Read UDP data off the wire
        if self.read_queue is not None:
            recv_data, recv_addr = self.read_queue.get()
        else:
            recv_data, recv_addr = self._sock.recvfrom(size)
            

        logger.debug("Read %d bytes."%len(recv_data))
        return recv_data, recv_addr
    
        
    def _get_read_response(self,length,read_multiple=False):
        """
        
        """
        data = ""
        if read_multiple:
            transaction_no = 0
        else:
            transaction_no = (self.transaction_no -1)%0x0000ffff
            
        
        while(len(data) < length):
            
            # Read a LO-PHI packet
            rapid_packet = self.get_rapid_packet()
            
            if rapid_packet.MAGIC_LOPHI != G.SENSOR_MEMORY.MAGIC_LOPHI:
                logger.error("Magic number mismatch. (%x)"%(rapid_packet.MAGIC_LOPHI))
                return None
            
            # Same transaction?
            if(rapid_packet.transaction_no != transaction_no):
                logger.error("different transaction! %x instead of %x"%(rapid_packet.transaction_no, 
                                                                             transaction_no))
                return None
            
            # Is this the correct response?
            if(rapid_packet.operation != G.SENSOR_MEMORY.COMMAND.READ + 0x2): # RAPID reply is 0x2
                logger.error("not a read?! {0}".format(rapid_packet.operation))
                logger.error(rapid_packet)
                continue
            
            if(rapid_packet.data is None or len(rapid_packet.data) != rapid_packet.length):
                logger.error("DATA LENGTHS DON'T MATCH! (Expected: %d, Got: %d bytes)"%(rapid_packet.length,
                                                                                        len(rapid_packet.data)))
            
            # Append our data
            data += rapid_packet.data
            
            # look for next transaction
            transaction_no = (transaction_no+1)%0x0000ffff

        # Just in case we read more than we wanted, truncate off the end bytes
        return (data[:length])
        
        return None
        
        
    def _read_from_sensor(self,address,length):
        """
            This is the lowest level read command and the only read command that
             will acctually perform a memory read from the sensor.
            
            @param address: Physical memory address to read
            @param length: Length of memory to read starting at @address 
            
            @TODO: Remove our horrible hack once the hardware is up-to-date
        """
        with network_lock:
            # This is a HACK to work around a bug in the PCI sensor that has trouble
            # when not reading on word boundaries?
            adjust_addr = 0
            
            # Is our start address word aligned?
            if address%4 != 0:
                adjust_addr = address%4
                address -= adjust_addr
                length += adjust_addr
                
            # Only read in words.
            adjust_len = 0
            if length%4 != 0:
                adjust_len = 4-length%4
                length += adjust_len
            
            self.transaction_no = 0
            rtn_data = ""
            
            remaining_length = length
            offset = 0
            
            if not self.use_threading:
                while remaining_length > 0:
                    # Calculate how much to read?
                    req_len = min(READ_CHUNK,remaining_length)
                    # Send our read command
                    
                    # Try to read RETRIES times
                    attempt = 0
                    while attempt < self.RETRIES:
                        try:
                            # Send read command
                            self._send_command(G.SENSOR_MEMORY.COMMAND.READ, 
                                               address+offset, 
                                               req_len)
                            # get data off the wire
                            tmp = self._get_read_response(req_len)
                            
                            # Something bad happen in the read, let's try to re-open the socket
                            if tmp is None:
                                logger.error("Didn't get a response from sensor. Trying again.")
                                self._disconnect()
                                self._connect()
                                continue
                            
                            break
                        
                        except socket.timeout:
                            logger.error("Memory sensor timeout (%d/%d)"%(attempt,
                                         self.RETRIES))
                            pass
                        
                        attempt += 1
                        
                    # if we hit our retries, the card has timed out.
                    if attempt == self.RETRIES:
                        logger.error("Memory sensor timed out! (0x%16X, %d)"%
                                     (address+offset,
                                     req_len))
                        raise socket.timeout

                    # If nothing came back, keep trying!
                    if tmp is None:
#                         continue
                        rtn_data = None
                        break
                    
                    rtn_data += tmp 
                    
                    # Calculate how much more we have to read
                    remaining_length -= req_len
                    offset += req_len
            
            else:
                # Try to read RETRIES times
                attempt = 0
                while attempt < self.RETRIES:
                    try:
                        
                        # Send all of our read commands
                        while remaining_length > 0:
                            # Calculate how much to read?
                            req_len = min(READ_CHUNK,remaining_length)
                            # Send our read command
                            self._send_command(G.SENSOR_MEMORY.COMMAND.READ, address+offset, req_len)
                        
                            # Calculate how much more we have to read
                            remaining_length -= req_len
                            offset += req_len
                            
                        # Read all of the data back at once.
                        rtn_data = self._get_read_response(length, True)
                        
                        # Something bad happen in the read, let's try to re-open the socket
                        if rtn_data is None:
                            logger.error("Didn't get a response from sensor. (%d/%d)"%(attempt,
                                     self.RETRIES))
                            time.sleep(1)
                            self._disconnect()
                            self._connect()
                            remaining_length = length
                        else:
                            break
                        
                    except socket.timeout:
                        logger.error("Memory sensor timeout (%d/%d)"%(attempt,
                                     self.RETRIES))
                        pass
                    
                    attempt += 1
                        
                if attempt == self.RETRIES:
                    logger.error("Memory sensor timed out! (0x%16X, %d)"%
                                 (address,
                                 length))
                    raise socket.timeout
                    
                
        
    
            # return the read data
            # HACK: start from our offset and truncate extra data appended to ensure
            # that we were word-aligned
            if rtn_data is None:
                return rtn_data
            else:
                return rtn_data[adjust_addr:length-adjust_len]
        
    
    
    
        
    def get_rapid_packet(self):
        """
            Read the next memory sensor packet from the wire.
            
            @return: LO-PHI packet as a dictionary 
                - lophi_header: LO-PHI defined header
                - lophi_data:  
        """
        # Read data off the wire
        logger.debug("Reading LO-PHI packet...")
        recv_data, recv_addr = self._read_raw_packet()

        network_packet = MemoryRapidPacket(recv_data)

#         logger.info("Received: %s"%network_packet)        
        return network_packet
    
    
    def write(self,address,data):
        """
            Write data to physical memory
        """
        from lophi.data import DataStruct
        class MemoryWritePacket(DataStruct):
            """
                This defines the header used by then RAPID protocol, which is abused
                by our memory sensors.
            """
            name = "RAPIDPacket"
            STRUCT = [('MAGIC_LOPHI','!I'),
                      ('transcation_no','!H'), 
                      ('operation','!B'), 
                      ('address','!7xQ'), 
                      ('length','!I')
                      ]
        
        write_packet = MemoryWritePacket()
        write_packet.address = address
        write_packet.data = data
        write_packet.length = len(data)
        write_packet.operation = G.SENSOR_MEMORY.COMMAND.WRITE
        write_packet.MAGIC_LOPHI = G.SENSOR_MEMORY.MAGIC_LOPHI
        
        # Keep trying to reconnect
        while not self._connect():
            time.sleep(1)
        
        # Send payload to our sensor
        sent = self._sock.send(`write_packet`)
        if sent != len(write_packet):
            logger.error("Only sent {0} out of {1}".format(sent, len(write_packet)))
            dead = True
    
    
            
                
                
                
        