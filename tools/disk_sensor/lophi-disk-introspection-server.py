import socket
import multiprocessing
import os
import time
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)

import lophi.globals as G
from lophi.data import DiskSensorPacket, DataStruct

class MetaHeader(DataStruct):
    STRUCT = [('filename','1024s'),
              ('sector_size','I')]
    

disk_stream_dict = multiprocessing.Manager().dict()

class VMIntrospection(multiprocessing.Process):
    """
        This class will handle data forwarding for the VM it was initialized 
        for.
    """
    def __init__(self, conn, addr):
        """
            @param conn: connection descriptor
            @param addr: address information of client
        """
        self._conn = conn
        self._addr = addr
        
        multiprocessing.Process.__init__(self)
        
        
    def run(self):
        """
            Run forever grabbing data from the VM and forwarding it to listening
            clients 
        """
        # Get our meta data which is always the first packet sent
        meta = MetaHeader()
        meta_data = self._conn.recv(len(meta))
        if len(meta_data) == 0:
            logger.debug("VM Disconnected.")
            self._conn.close()
            return
        
        meta._unpack(meta_data)
        
        #logger.debug("Got meta data")
        #logger.debug(meta)
        
        # Store our filename for this VM
        # NOTE: We must strip the null chars off or comparisons will fail!
        filename = meta.filename.strip("\x00")
        
        # Create our sensor packet, and save its default size
        sensor_packet = DiskSensorPacket()
        sensor_header_size = len(sensor_packet)
        
        # Read packets forever
        while True:
            
            # Read and unpack our header
            header_data = self._conn.recv(sensor_header_size)
            if len(header_data) == 0:
                #logger.debug("VM Disconnected.")
                break
            
            sensor_packet._unpack(header_data)
            
            # Get the accompanying data
            try:
                sensor_packet.data = self._conn.recv(sensor_packet.size)
            except:
                print sensor_packet
                G.print_traceback()
                
            if len(sensor_packet.data) == 0:
                logger.debug("VM Disconnected.")
                self._conn.close()
                return
            
            if filename in disk_stream_dict:
                #logger.debug("Found %s in dict."%filename)
                for queue in disk_stream_dict[filename]:
                    queue.put(`sensor_packet`)
                    
            #logger.info(sensor_packet)
        
        
class LOPHIClient(multiprocessing.Process):
    """
        This class will handle all "listeners" and forward the requested disk
        activity stream 
    """
    def __init__(self, conn, addr):
        """
            @param conn: connection descriptor
            @param addr: address information of client
        """
        self._conn = conn
        self._addr = addr
        
        multiprocessing.Process.__init__(self)


    def run(self):
        """
            Run forever grabbing data from the VM and forwarding it to listening
            clients 
        """
        
        sensor_queue = multiprocessing.Manager().Queue()
        while True:
            cmd = self._conn.recv(2048)
            
            #logger.debug("Got command: %s"%cmd)
            
            cmd_split = cmd.split(" ")
            
            if cmd_split[0] == "n":
                filename = cmd_split[1].strip(' \t\n\r')
                if filename not in disk_stream_dict:
                    disk_stream_dict[filename] = []
                    
                shared_list = disk_stream_dict[filename]
                shared_list.append(sensor_queue)
                disk_stream_dict[filename] = shared_list
                
                #logger.debug("Added queue to shared list.  Waiting for data...")
        
                while True:
                    sensor_packet = sensor_queue.get()
                    self._conn.send(sensor_packet)
                     
               
class IntrospectionServer(multiprocessing.Process):
    """
        This class accepts connections from the VMs and spins off threads for 
        each.
    """
    def __init__(self):
        """ Initialize our class """
        self.SOCKET_NAME = "/tmp/lophi_disk_socket"
        self._sock = None
        
        multiprocessing.Process.__init__(self)
        
        
    def _connect(self):
        """
            Bind to our UNIX socket the VMs will connect to
        """
        # See if we need to clean up our socket
        if os.path.exists(self.SOCKET_NAME):
            os.unlink(self.SOCKET_NAME)
        
        # Bind our socket
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(self.SOCKET_NAME)
        
        # Ensure other UIDs can speak to us
        os.chmod(self.SOCKET_NAME, 0777)
        
        # Listen for incoming connections
        self._sock.listen(5)
        
    def run(self):
        """
            Listen forever for connecting virtual machines
        """
        self._connect()
        
        while True:
            conn,addr = self._sock.accept()
            #logger.debug("Got connection %s %s"%(conn, addr))
        
            VMIntrospection(conn,addr).start()
            
    def __del__(self):
        """
            Be sure to always clean up our socket
        """
        if self._sock is not None:
            self._sock.close()
            os.unlink(self.SOCKET_NAME)
            
            
class LOPHIServer(multiprocessing.Process):
    """
        This class will accept connections from LO-PHI sensor to retrieve 
        streams of disk activity
    """
    def __init__(self, port=G.SENSOR_DISK.DEFAULT_PORT):
        """ Initialize our class """
        self.PORT = port
        self._sock = None
        
        multiprocessing.Process.__init__(self)
        
        
    def _connect(self):
        """
            Bind to our UNIX socket the VMs will connect to
        """
        while True:
            try:
                # Bind our socket
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.bind(('',self.PORT))
                
                # Listen for incoming connections
                self._sock.listen(5)
                
                break
            except:
                print "* Could not bind socket, retrying in 5 seconds..."
                time.sleep(5)
        
    def run(self):
        """
            Listen forever for connecting virtual machines
        """
        self._connect()
        
        print "Waiting for connections"
        while True:
            conn,addr = self._sock.accept()
            print "Got connection", conn, addr
        
            LOPHIClient(conn,addr).start()
            
    def __del__(self):
        """
            Be sure to always clean up our socket
        """
        if self._sock is not None:
            self._sock.close()
            
            
intro_server = IntrospectionServer()
lophi_server = LOPHIServer()

intro_server.start()
lophi_server.start()
intro_server.join()
lophi_server.join()
