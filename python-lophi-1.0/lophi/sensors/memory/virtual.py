"""
    Class for interacting with our VM introspection server (memory)

    (c) 2015 Massachusetts Institute of Technology
"""
#Native
import socket
import os
import time
import logging
logger = logging.getLogger(__name__)


# LO-PHI
from lophi.sensors.memory import MemorySensor
from lophi.data import KvmMemRequest


class MemorySensorVirtual(MemorySensor):
    """"
        Our virtual memory sensor is just an interface to virsh and a UNIX 
        socket.
    """
    class CMD_TYPE:
        QUIT = 0
        READ = 1
        WRITE = 2
        
        
    def __init__(self, vm_name, cache_timeout=0):
        """ Initialize our class """
        self.vmi = None
        
        # Ensure that we are root
        if not os.geteuid() == 0:
            logger.error("WARNING: Memory sensor should be run as root!")
        
        # Initialize our sensor
        self.vm_name = vm_name
        self.name = vm_name+"-MemorySensor"
        
        # Caching
        self.cache = {}
        self.cache_timeouts = {}
        self.CACHE_TIMEOUT = cache_timeout # seconds
        
        # Bad Memory regions
        self.BAD_MEM_REGIONS = [(0x0, 4096)]
         
        self.SOCK = None
        self.RETRIES = 3
         
        MemorySensor.__init__(self)
        
        
    def __del__(self):
        """ Try to cleanup nicely """
        self._disconnect()

    def _exec_qmp(self, cmd):
        """
            Execute a Qemu Monitor Protocol command
            
            @param cmd: Command to execute (E.g. { "execute": "qmp_capabilities" })
        """
        from subprocess import Popen, PIPE
        
        shell_cmd = ["virsh", "qemu-monitor-command", self.vm_name, cmd]
        process = Popen(shell_cmd, stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = int(process.wait())
        
        return (output, exit_code)
        
    
    def _connect(self):
        """
            Try to connect to the VM using qmp
        """
        if self.SOCK is not None:
            return True
        
        logger.info("Connecting to KVM instance. (%s)"%self.vm_name)
        
        tmp_name =  "vmi-"+self.vm_name
        tmp_path = os.path.join("/tmp",tmp_name)
        
        cmd = '{"execute": "pmemaccess", "arguments": {"path": "%s"}}'%tmp_path
        
        # While the exit code is not 0, retry (Machine just not on yet?)
        if self._exec_qmp(cmd)[1] != 0:
            logger.warn("Could not connect to guest %s... (Retrying)"%
                        self.vm_name)
            return False
        
        try:
            self.SOCK = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.SOCK.connect(tmp_path)
            
            logger.info("Connected to %s."%tmp_path)
        except:
            logger.warn("Could not connect to memory sensor. (%s @ %s)"%(
                                                                self.vm_name,
                                                                tmp_path))
            return False
        
        return True
    
    
    def _disconnect(self):
        """
            Disconnect from our host
        """
        if self.SOCK is not None:
            self.SOCK.close()
            self.SOCK = None            
                
                
    def _read_from_sensor(self, address, length):
        """
            Read physical memory
            
            @param address: Address to start reading from
            @param length: How much memory to read
            
            @TODO: Fix KVM bug that doesn't allow reading the first page of memory!
        """                

         
        logger.debug("Sending memory read request to hypervisor. (%016X, %d)"%(
                                                                        address, 
                                                                        length))
        
        # Construct our request
        req = KvmMemRequest()
        req.type = self.CMD_TYPE.READ
        req.address = address
        req.length = length
         
         
        # Try RETRIES time to read from the guest system
        read = ""
        for retry in range(3):
            if not self._connect():
                logger.error("No VM connected.")
                return None
            read = ""
            try:
                self.SOCK.settimeout(1)
                
                # Send our request
                self.SOCK.send(`req`)
                
                # Get our response
                
                while len(read) < length:
                    read += self.SOCK.recv(length+1)
                    
                    # Optimization if all of the bits are 1
                    if len(read) == 1 and read == "\xff":
                        read = "\xff"*length+"\x01"
                        
                self.SOCK.settimeout(None)
            except:
                logger.error("Failed to read from sensor. (Attempt %d/%d)"%(
                                                                retry,
                                                                self.RETRIES))
                import traceback
                traceback.print_exc()
                self._disconnect()
        
        logger.debug("Read %d bytes"%len(read))
        
        # Did we get all of our data?
        if len(read) != length+1:
            logger.error("Could not read memory from sensor. (Addr: %016X, Len: %d, %s)"%(
                                                                                          address,
                                                                                          length,
                                                                                          self.vm_name))
            logger.error("Got %d bytes, expected %d"%(len(read),length))
            return None
         
        # extract portions of our resposne
        status = read[-1]
        data = read[:-1]
        
        # What is our status as reported by the hypervisor?
        if status == 0:
            logger.error("Error in memory read, reported by guest. (Addr: %016X, Len: %d, %s)"%(
                                                                                          address,
                                                                                          length,
                                                                                          self.vm_name))
            return None
        
        return data

        
    def write(self,address, data):
        """
            Write to physical memory
            
            @param addr: Address to start writing to
            @param data: Data to be written to memory
            
            @return: True/False
        """
        if not self._connect():
            logger.error("No VM connected.")
            return False
         
        logger.debug("Sending memory write request to hypervisor.")
         
        # Construct our request
        req = KvmMemRequest()
        req.type = self.CMD_TYPE.WRITE
        req.address = address
        req.length = len(data)
        req.data = data
        
        try:
            # Send our request
            self.SOCK.send(`req`)
            
            # Get our response
            status = self.SOCK.recv(1)
        except:
            logger.error("Failed to write to memory sensor")
            self._disconnect()
            return None
        
        # What is our status as reported by the hypervisor?
        if status == '\x00':
            logger.error("Error in memory ready, reported by guest. (%s)"%
                         self.vm_name)
            return False
        
        return True
    
    
    def get_vcpureg(self, register, value):
        """
            Get the register value from the guest using qmp
            
            @param register: Register to get value of
            @param value: ?? Not sure... ??
        """
        register = register.upper()
        logger.info("Getting register value of %s (%s)"%(register, value))
        
        reg_cmd = '{"execute": "human-monitor-command", "arguments": {"command-line": "info registers"}}'
        
        regs = self._exec_qmp(reg_cmd)
        if regs[1] != 0:
            logger.error("Could not get register values.")
            return 0
        
        # extract our actual return data
        import json
        reg_data = json.loads(regs[0])['return']
        
        
        # Find the value of the register in question
        import re
        search = re.search('%s=([a-fA-F0-9]+)'%register, reg_data)
        if search is None:
            logger.error("Could not find register. (%s)"%register)
            return 0
        
        reg_value = int(search.group(1),16)
        # Print the actual value
        return reg_value
