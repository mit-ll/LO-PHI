"""
    Class to eventually interface with physical CPUs using either DSTREAM or
    XDP

    (c) 2015 Massachusetts Institute of Technology
"""
import logging
logger = logging.getLogger(__name__)

from lophi.sensors.cpu import CPUSensor
import lophi.globals as G


class CPUSensorPhysical(CPUSensor):
    
    def __init__(self, sensor_ip, sensor_port=G.SENSOR_CPU.DEFAULT_PORT, name=None):
        """ Initialize our sensor """
        
        # Set our variables
        self.sensor_ip = sensor_ip
        self.sensor_port = sensor_port
        
        if name is not None:
            self.name = name
            
        CPUSensor.__init__(self)