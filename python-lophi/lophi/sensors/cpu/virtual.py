"""
    Class to eventually interact with virtual CPUs

    (c) 2015 Massachusetts Institute of Technology
"""
import logging
logger = logging.getLogger(__name__)

from lophi.sensors.cpu import CPUSensor

class CPUSensorVirtual(CPUSensor):
    
    def __init__(self, vm_name):
        """ Initialize our sensor """
        
        # Set our variables
        self.vm_name = vm_name
        self.name = vm_name+"-CPUSensor"
        
        CPUSensor.__init__(self)