"""
    Abstract class for interacting with the SUT's CPU

    (c) 2015 Massachusetts Institute of Technology
"""
from lophi.sensors import Sensor

class CPUSensor(Sensor):
    """"
        This is an abstract class to help manage both physical and virtual
        implementations.  This will also allow us to expand to new 
        implementations very easily.
    """
    
    
    def __init__(self):
        """ Initialize our class """
        # Ensure that this class is never initialized
        if self.__class__ == CPUSensor:
            raise("Interface initialized directly!")
        
        Sensor.__init__(self)
        
        
    def read_all_registers(self):
        """ Read all registers from a CPU """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def write_all_registers(self):
        """ Write all registers to a CPU """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def pause(self):
        """ Pause the CPU """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def resume(self):
        """ Resume CPU """
        raise NotImplementedError("ERROR: Unimplemented function.")