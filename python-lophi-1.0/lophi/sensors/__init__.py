"""
    Abstract class for our sensors

    (c) 2015 Massachusetts Institute of Technology
"""
import logging
logger = logging.getLogger(__name__)

class Sensor:
    """
        This is the abstract class that encompasses all sensors
    """
    
    sensor_count = 1
    
    def __init__(self):
        """
            Give every sensor a generic name when it's initialized
        """
        self.id = self.__class__.__name__ + "-" + str(self.sensor_count)
        self.sensor_count += 1
        self.assigned_to_machine = False
        
        if "name" not in self.__dict__ or self.name is None:
            logger.warning("Sensor initialized without a name. (%s)"%self.id)
            self.name = self.id
        
        logger.debug("Initialized Sensor (%s)"%self.id)
        
    def is_assigned(self):
        """
            Check to see if this sensor has been assigned a machine yet
            
            @return: True/False
        """
        return self.assigned_to_machine
    
    def set_assigned(self, a=True):
        """
            Set the assigned status of the machine
            
            @param a: True/False
        """
        self.assigned_to_machine = a
        
    def set_id(self,identifier):
        """
            Update the sensor with a user-defined ID
            
            @param identifier: Unique identifier used to manage sensor  
        """
        self.id = identifier
        
        
#     def __str__(self):
#         """
#             Print basic sensor stuff
#         """
#         o = "[Sensor %s]"%self.id
# #         o += " type: %s"%self.__class__.__name__
#         o += " used: %s"%self.assigned_to_machine
#         
#         return o
        