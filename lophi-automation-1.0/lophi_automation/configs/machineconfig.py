"""
    Class of handling configuration files for physical machines

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import logging
logger = logging.getLogger(__name__)

# LO-PHI Automation
from lophi_automation.configs import LophiConfig

class MachineConfig(LophiConfig):
    """
        Very simple class to hand around and leave room for improvement in the 
        future
    """

    def __init__(self, name, Config=None):
        """
            Initialize all of our variables and set any new settings that were
            specified in the config file.
        """

        # Set our name
        self.name = name

        if Config is None:
            logger.error("Empty config was given.")
            return None

        # Get our profile
        if not self._get_option(Config, name, "volatility_profile"):
            logger.warning("An OS profile must be defined for semantic information.")
            
        # Memory Sensor?
        if self._get_option(Config, name, "memory_sensor"):
            if not self._get_option(Config, name, "ram_size"):
                logger.warning("RAM size must be given with memory sensors for semantic information.")
                
        # Disk Sensor?
        if self._get_option(Config, name, "disk_sensor"):
            if not self._get_option(Config, name, "disk_scan"):
                logger.warning("A scan image must be provided with disk sensors for semantic information. ")
                
        # Control Sensor?
        self._get_option(Config, name, "control_sensor")
        
        # CPU Sensor
        self._get_option(Config, name, "cpu_sensor")
        
        # Network Sensor
        self._get_option(Config, name, "network_sensor")
        
        # Mac Address
        self._get_option(Config, name, "mac_address")
        
        # DHCP_Server
        self._get_option(Config, name, "dhcp_server")
        
        # Additional (optional) parameters
        self._get_option(Config, name, "mac_addr")
