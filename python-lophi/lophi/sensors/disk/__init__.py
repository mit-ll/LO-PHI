"""
    Abstract class to interact with disk sensor

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import struct

# LO-PHI
from lophi.sensors import Sensor

class DiskSensor(Sensor):
    """"
        This is an abstract class to help manage both physical and virtual
        implementations.  This will also allow us to expand to new 
        implementations very easily.
    """
    
    
    def __init__(self):
        """ Initialize our class """
        # Ensure that this class is never initialized
        if self.__class__ == DiskSensor:
            raise("Interface initialized directly!")
        
        Sensor.__init__(self)
        
        
    def _connect(self):
        """ Connect to our sensor """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def _disconnect(self):
        """ Disconnect from our sensor """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def get_disk_packet(self):
        """ Get the next packet header/data """
        raise NotImplementedError("ERROR: Unimplemented function.")
