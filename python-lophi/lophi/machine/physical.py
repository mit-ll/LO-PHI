"""
    Class for easily interacting with physical machines

    (c) 2015 Massachusetts Institute of Technology
"""
import logging
logger = logging.getLogger(__name__)
import time

from lophi.machine import Machine
import lophi.globals as G

DISK_REVERT_TIMEOUT = 10*60 # 15 Minutes

class PhysicalMachine(Machine):
    """
        This class is meant to be an abstract clas that is used to interface
        with Physical Machines
    """
    IS_VM = False
    MACHINE_TYPE = G.MACHINE_TYPES.PHYSICAL
    MACHINE_STATE = G.MACHINE_STATES['UNKNOWN']
    DISK_STATE = G.DISK_STATES['UNKNOWN']

    def __init__(self, config):
        """
            Initalize anythign that we need and save our config file.
        """
        
        self.type = G.MACHINE_TYPES.PHYSICAL
        
        Machine.__init__(self, config)
        
    def lophi_init(self, force_new):
        """
            This will get our machine ready to be used with LO-PHI
        """
        print "No physical control available at this point..."


    def set_volatility_profile(self, profile_name):
        """
            Set the profile of this machine.  
            
            In a physical system this will change the pxe image that it restores
            from, if one exists.
            
            In a virtual system, this will change which base disk image we use.
            
            @param profile_name: Profile name of system, based on Volatility's
                                    naming scheme.
        """
        self.config.volatility_profile = profile_name
        
        if self.config.mac_address is None:
            logger.error("No MAC address provided for %s."%self.config.name)
            return False
        
        if self.pxe_server is None:
            logger.error("No PXE/DHCP server provided for %s to resolve IP."%self.config.name)
            return False
        
        if profile_name.lower() in self.images_map:
            pxe_config_file = self.images_map[profile_name.lower()] 
        
            logger.debug("Setting PXE image to %s for %s"%(pxe_config_file,
                                                           self.config.name))
            
            # Set image on the PXE server
            return self.pxe_server.set_pxe_conf(self.config.mac_address, pxe_config_file)
        else:
            logger.error("No PXE image exist for this profile. (%s)"%profile_name)
            return False

    """
                Actuation Functions
    """
    # Defined in Machine


    """
                Memory Functions
    """
    # Read and write defined in Machine

    
    
    def memory_get_size(self):
        """
            Get the memory size of our machine
            
            @return: returns the memory size based on our config.get
        """
        return int(self.config.ram_size)


    """
                Power functions
    """
    # Defined in Machine
    
    """
                Machine Control Functions
    """
    # Not yet available for physical machines

    """
        Snapshot Functions
    """

    def machine_reset(self):
        """
            Reset the machine back to the original state of the saved state
        """

        # we only have disk reverting capability for now
        if self.pxe_server is None:
            logger.error("We do not know the PXE server for this physical machine -- cannot guarantee correct reset.")
            return False
        
        return self.disk_revert()

    
    """
        Disk Functions
    """
    
    def disk_revert(self):
        """
            Overwrite the disk with a backup of our most recent snapshot
        """
        
        if self.config.mac_address is None:
            logger.error("No MAC address provided for %s."%self.config.name)
            return False
        
        if self.pxe_server is None:
            logger.error("We do not know the PXE server for this physical machine -- cannot revert disk automatically.")
            return False
        
        if not self._has_sensor('control'):
            logger.error("No control sensor for %s."%self.config.name)
            return False
        
        logger.info("Reverting physical disk . . . booting into clonezilla")
        
        # Turn machine off, if it's on
        self.power_off()
        
        # Let all the power cycle out
        time.sleep(10)
        
        # Enable PXE booting for our machine
        self.pxe_server.add_mac(self.config.mac_address)
        
        # Power on machine to start PXE/Clonzezilla restore
        self.power_on()
        
        # Just in case, let's wait a second or 2
        time.sleep(2)

        # machine will now PXE boot into Clonezilla which will run a batch job to revert the disk,
        # assuming that PXE and Clonezilla are configured correctly
        
        # Clonezilla should power off when we are done, return when we detect this
        logger.debug("Waiting for machine to power off (after clonezilla completes)...")
        offs = 0
        start = time.time()
        while True:
            # power status
            status = self.power_status()
            if status == G.SENSOR_CONTROL.POWER_STATUS.OFF:
                offs += 1
            else:
                offs = 0
                
            # Make sure the machien is really off
            if offs > 3:
                # machine is powered off
                logger.info("Disk revert complete.  Machine is powered off.")
                break
            
            if time.time()-start > DISK_REVERT_TIMEOUT:
                logger.error("Disk revert timeout!")
                return False
        
         # Let all the power cycle out
        time.sleep(5)
        
        # now return
        return True
    
    
    """
        Network Functions
    """
    def network_get_ip(self):
        """
            Looks up IP address from our DHCP server
            
            @return: ASCII IP address or None
        """
        
        if self.config.mac_address is None:
            logger.error("No MAC address provided for %s."%self.config.name)
            return None
        
        if self.pxe_server is None:
            logger.error("No PXE/DHCP server provided for %s to resolve IP."%self.config.name)
            return None
        
        # Resolve the IP from our PXE/DHCP server
        return self.pxe_server.get_ip(self.config.mac_address)
    
    
    """
        Miscellaneous Functions
    """
    def screenshot(self,filename,vol_uri=None):
        """
            Screenshot the display of the machine and save it to a file.
            
            @param filename: Filename to save screenshot data to. 
        """
        
        save_name = filename+".png"
        
        from lophi_semanticgap.memory.volatility_extensions import VolatilityWrapper
        
        if vol_uri is None:
            vol_uri = "lophi://"+self.memory.sensor_ip
            
        vol_profile = self.config.volatility_profile 
        vol = VolatilityWrapper(vol_uri,
                       vol_profile,
                       self.memory_get_size())
        
        screenshots = vol.execute_plugin("screenshot")
        
        # Loop over the returned sessions and only save the Default one.
        idx = 0
        for session in screenshots['HEADER']:

            if "Win7" in self.config.volatility_profile:
                if session == "session_1.WinSta0.Default":
                    screenshots['DATA'][idx].save(save_name,"PNG")
                    logger.debug("Saved Volatility screenshot to %s."%filename)
                    break
            elif session == "session_0.WinSta0.Default":
                
                screenshots['DATA'][idx].save(save_name,"PNG")
                logger.debug("Saved Volatility screenshot to %s."%filename)
                break
                
            idx += 1
            
        return save_name
        
      
