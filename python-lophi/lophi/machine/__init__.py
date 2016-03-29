"""
    Abstract machine class to handle all of the interactions with a virtual
    or physical machine.

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import os
import shutil
import socket
import logging
import time
import multiprocessing
logger = logging.getLogger(__name__)

# LO-PHI
from lophi.sensors import Sensor
from lophi.sensors.memory import MemorySensor
from lophi.sensors.disk import DiskSensor
from lophi.sensors.control import ControlSensor
from lophi.sensors.cpu import CPUSensor
from lophi.sensors.network import NetworkSensor
import lophi.network.ping as ping
import lophi.globals as G


class Machine:
    """
        Abstract class used to control a machine.  Physical, Xen, or otherwise.
    """

    ALLOCATED = -1
    MACHINE_STATE = G.MACHINE_STATES['UNKNOWN']
    DISK_STATE = G.DISK_STATES['UNKNOWN']

    def __init__(self, machine_config):
        """
            Initialize anything that we need and save our config file.
        """
        # Ensure that this class is never initialized
        if self.__class__ == Machine:
            raise("Abstract class initialized directly!")
        
        # Save our config
        self.config = machine_config

        # initialize our sensors
        self.control = None
        self.disk = None
        self.memory = None
        self.cpu = None
        self.network = None
        
        self.pxe_server = None
        
        self.images_map = None
        
        self.MUTEX = multiprocessing.Lock()
    
    def _has_sensor(self,name):
        """
            See if a sensor was defined
            
            @return: True if a memory sensor exists, False otherwise
        """
        if name not in self.__dict__ or self.__dict__[name] is None:
            logger.warning("No %s sensor has been defined for %s"%(name,
                                                                   self.config.name))
            return False
        else:
            return True

    def set_volatility_profile(self, profile_name):
        """
            Set the profile of this machine.  
            
            In a physical system this will change the pxe image that it restores
            from, if one exists.
            
            In a virtual system, this will change which base disk image we use.
            
            @param profile_name: Profile name of system, based on Volatility's
                                    naming scheme.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def get_volatility_profile(self):
        """
            Get the volatility profile of this machine
        """
        if "volatility_profile" in self.config.__dict__:
            return self.config.volatility_profile
        else:
            return None

    def add_sensors(self,sensor_list):
        """
            Given a list of all of our initialized sensors this will try to 
            assign all of those requested by this machine.
        """
        
        if self.type != G.MACHINE_TYPES.PHYSICAL:
            logger.debug("Virtual sensors are automatically added, no need to call add_sesnors.")
            return
        
        rtn = []
        
        def add(sensor):
            """ Add sensor to machine """
            if self.add_sensor(sensor):
                rtn.append(sensor)    
            
        # Mem
        add(sensor_list.get(self.config.memory_sensor))
        # CPU
        add(sensor_list.get(self.config.cpu_sensor))
        # Disk
        add(sensor_list.get(self.config.disk_sensor))
        # Control
        add(sensor_list.get(self.config.control_sensor))
        # Network
        add(sensor_list.get(self.config.network_sensor))
            
        return rtn


    def add_sensor(self,sensor):
        """
            Add a sensor to our machine
            
            @param sensor: Sensor class will be detected  
        """
        if sensor is None:
            return False
        if sensor.is_assigned():
            logger.error("Tried to add sensor (%s) that was already in use to machine (%s)."%(sensor.id,
                                                                                              self.config.name))
        
        from lophi.machine.virtual import VirtualMachine
        from lophi.machine.physical import PhysicalMachine
        
        # Make sure it's a sensor being added
        if not issubclass(sensor.__class__,Sensor):
            logger.error("Must only add sensors which are subclasses of Sensor")
            return False
        
        # Ensure sensor and machine match
        if isinstance(self,VirtualMachine) and str(sensor.__class__).find("physical") != -1:
            logger.error("Tried to add physical sensor to virtual machine.")
            return False
        if isinstance(self,PhysicalMachine) and str(sensor.__class__).find("virtual") != -1:
            logger.error("Tried to add virtual sensor to physical machine.")
            return False
        
        if issubclass(sensor.__class__,DiskSensor):
            self.disk = sensor
        elif issubclass(sensor.__class__,ControlSensor):
            self.control = sensor
        elif issubclass(sensor.__class__,MemorySensor):
            self.memory = sensor
        elif issubclass(sensor.__class__,CPUSensor):
            self.cpu = sensor 
        elif issubclass(sensor.__class__,NetworkSensor):
            self.network = sensor 
        else:
            logger.error("Sensor type %s is not recognized for virtual machines."%
                          sensor.__class__)
            return False
        
        sensor.set_assigned()
        
        return True            

    def add_pxe_server(self, pxe_server):
        """
            Add a PXE server to this machine for resetting machine state.
            
            @param pxe_server: PXE Server object
        """
        from lophi.machine.physical import PhysicalMachine
        
        if not isinstance(self,PhysicalMachine):
            logger.warn("Tried to add a PXE server a non-physical machine. (%s/%s)"%(self.config.name,self.__class__))
            return False
        
        self.pxe_server = pxe_server
        
        # Set our profile so PXE can know what to revert from
        self.set_volatility_profile(self.config.volatility_profile)
        
        return True
    
    def add_image_map(self, images_map):
        """
            Add a mapping of profile names to disk images (Virtual or physical)
            Assumed that the map is only for this machine type
            
            @param images_map: Profile -> Image dict. (For Physical this is the
            PXE name, for Virtual this is an actual filename) 
        """
        logger.debug("Added profile to image map. (%s)"%self.config.name)
        self.images_map = images_map

    """
        Actuation Functions
    """
    def keypress_send(self, keypresses):
        """
            Given a list of keypress instructions will emulate them on the SUT.
            
            @param keypresses: list of commands returned from a 
                                KeypressGenerator to send to keyboard emulator
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        self.control.keypress_send(keypresses)
    
    def keypress_get_generator(self):
        """
            Return a generator to convert scripts into a language this sensor 
            understands
            
            @return: KeypressGeneratorPhysical or KeypressGeneratorVirtual
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        return self.control.keypress_get_generator()
        
        
    def mouse_click(self,x,y,button=None,double_click=False):
        """
            This will move the mouse the specified (X,Y) coordinate and click
        """
        if not self._has_sensor("control"):
            return
        
        return self.control.mouse_click(self,x,y,button,double_click)
    
    
    """
        Memory Functions
    """

    def memory_read(self, addr, length):
        """
            Read physical memory
            
            @param addr: Address to start reading from
            @param length: How much memory to read
        """
        # Check for sensor
        if not self._has_sensor("memory"):
            return None
        
        try:
            data = self.memory.read(addr,length)
            return data
        except:
            logger.error("Memory read failed. (Addr: 0x%x, Len: %d)"%(addr,length))
            G.print_traceback()
            return None


    def memory_write(self, addr, data):
        """
            Write physical memory
            
            @param addr: Address to start writing to
            @param data: Data to be written
        """
        # Check for sensor
        if not self._has_sensor("memory"):
            return False
        
        return self.memory.write(addr,data)

    def memory_get_size(self):
        """
            Get the memory size of our machine
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def memory_dump(self,filename):
        """
            Dump the memory of the machine to the given filename
           
           WARNING: The current implementation reads the entire image into 
           memory first.
               
            @param filename: Filename to dump a memory image to
        """
        try:
            f = open(filename,"w+")
        except:
            logger.error("Could not create %s"%filename)
            return False
        
        total_size = self.memory_get_size()
        
        offset = 0
        from lophi.sensors.memory import CACHE_CHUNK
        rtn = True
        
        while offset < total_size:
            memory = self.memory_read(offset, min(CACHE_CHUNK,total_size-offset))
            
            if memory is None:
                logger.error("Memory dump failed!")
                rtn = False
                break
            
            f.write(memory)
            
            offset += CACHE_CHUNK
            
        f.close()
        
        return rtn


    """
        Power Functions
    """
    
    def power_on(self):
        """
            Power on the machine
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        logger.debug("Powering on machine. (%s)"%self.config.name)
        if self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.ON:
            rtn = self.control.power_on()
            
            while rtn and self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.ON:
                pass
        
            return rtn
        else:
            return True
        
        
    def power_shutdown(self):
        """
            Nice shutdown of the VM
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        logger.debug("Shutting down machine. (%s)"%self.config.name)
        return self.control.power_shutdown()
        # Update state variable
        self.MACHINE_STATE = G.MACHINE_STATES['OFF']


    def power_off(self):
        """
            Hard shutdown the machine
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        logger.debug("Powering off machine. (%s)"%self.config.name)
        
        if self.power_status() == G.SENSOR_CONTROL.POWER_STATUS.ON:
            rtn = self.control.power_off()
        
            start = time.time()
            while rtn and self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.OFF:
                
                time.sleep(1)
                
                if time.time()-start > 10:
                    logger.error("Machine did not power off after 10 s. Trying again.")
                    rtn = self.control.power_off()
                    
                pass
        
            return rtn
        else:
            return True
        
        
    def power_reset(self):
        """
            Reset the power on the machine
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        logger.debug("Resetting machine. (%s)"%self.config.name)
        return self.control.power_reset()
    
    
    def power_reboot(self):
        """
            Soft reboot the machine
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        logger.debug("Rebooting machine. (%s)"%self.config.name)
        return self.control.power_reboot()
    
    def power_status(self):
        """
            Get the power status of the machine.
            @return:  ON, OFF, UNKNOWN
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        status = self.control.power_status()
        logger.debug("Getting power status of machine. (%s/%s)"%(self.config.name,status))
        return status
    
    
    """
        Machine Control Functions
    """
    
    def machine_create(self, paused=False):
        """
            configure a new machine from the specified config file.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def machine_pause(self):
        """
            Pause a machine
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def machine_resume(self):
        """
            Resume a paused machine
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    
    """
        Snapshot Functions
    """

    def machine_save(self):
        """
            Suspends machine and saves state to a file.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def machine_restore(self, paused=False):
        """
            Restore a machine from our saved state and start it
        """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def machine_snapshot(self):
        """
            Takes a snapshot of the machine and freezes it temporarily.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def machine_snapshot_restore(self):
        """
            Restore a machine from our snapshotted state and start it
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def machine_reset(self):
        """
            Reset the machine back to the original state of the snapshot
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return

        # Ensure that our machine is pwered down
        if self.control.power_status() != G.SENSOR_CONTROL.POWER_STATUS.OFF:
            logger.debug("Powering down machine...")
            self.control.power_off()

        # Revert our disk
        logger.debug("Reverting disk...")
        return self.disk_revert()


    """
        Disk Functions
    """

    def disk_revert(self):
        """
            Overwrite the disk with a backup of our most recent snapshot
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def disk_get_packet(self):
        """
            Get the next DiskSensorPacket off the wire.
            
            @return: DiskSensorPacket  
        """
        return self.disk.get_disk_packet()
    
    
    """
        Network Functions
    """
    def network_get_ip(self):
        """
            Looks up IP address from our DHCP server
            
            @return: ASCII IP address or None
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def network_get_status(self):
        """
            Get the network status of this machine
            Returns True if machine is up, and False otherwise
            
            @return: True for UP, False for DOWN
        """
        ip = self.network_get_ip()
                
        if ip is None:
            logger.debug("Cannot get net status -- don't know this machine's IP!")
            return False

        # Use ping to determine if the machine is up
        logger.debug("Pinging %s..."%ip)
        resp = ping.echo(ip, timeout=1)
        
        if resp:
            return True
        else:
            return False
        
        
    def network_read(self):
        """
            Read a network packet from our network sensor
            
            @return: (timestamp,packet) tuple for the next network packet on 
                        the wire. 
        """
        # Check for sensor
        if not self._has_sensor("network"):
            return None
        
        return self.network.read()
    
    
    def network_write(self,data):
        """
            Write a raw network packet to the interface
            
            @param data: Raw network packet
        """
        # Check for sensor
        if not self._has_sensor("network"):
            return None
        
        return self.network.write(data)
        
        
    """
        Miscellaneous Functions
    """
    def screenshot(self,filename,vol_uri=None):
        """
            Screenshot the display of the machine and save it to a file.
            
            @param filename: Filename to save screenshot data to.
            @param vol_uri: Just here to be compatible with Physical
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    # Useful debug type stuff
    def __str__(self):
        """
            Just output a nice pretty string of our params
        """
        rtn = "[%s]\n" % self.config.name

        rtn += "  ALLOCATED=%s\n" % (self.ALLOCATED)
        rtn += "  STATE=%s\n" % (self.MACHINE_STATE)
        rtn += "  DISK_STATE=%s\n" % (self.DISK_STATE)
        rtn += "  MACHINE_TYPE=%s\n" % (self.type)
        for k in self.config.__dict__.keys():
            if k is not "name":
                rtn += "  %s=%s\n" % (k, self.config.__dict__[k])
        return rtn


