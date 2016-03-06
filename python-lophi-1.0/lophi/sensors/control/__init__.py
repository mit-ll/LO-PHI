"""
    Abstract class for control sensors

    (c) 2015 Massachusetts Institute of Technology
"""
from lophi.sensors import Sensor

class ControlSensor(Sensor):
    
    """"
        This is an abstract class to help manage both physical and virtual
        implementations.  This will also allow us to expand to new 
        implementations very easily.
    """
    

    def __init__(self):
        """ Initialize our class """
        # Ensure that this class is never initialized
        if self.__class__ == ControlSensor:
            raise("Interface initialized directly!")
        
        Sensor.__init__(self)
    
    
    def _connect(self):
        """
            Connect to the actuation interface.
            E.g. Arduino for physical, libvirt for virtual machines
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def _disconnect(self):
        """
            Disconnect to the actuation interface.
            E.g. Arduino for physical, libvirt for virtual machines
        """
        raise NotImplementedError("ERROR: Unimplemented function.")  

    def mouse_click(self,x,y,button,double_click):
        """
            This will move the mouse the specified (X,Y) coordinate and click
        """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def mouse_wiggle(self, enabled):
        """ This function randomly wiggles the mouse """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def keypress_send(self, keypresses):
        """
            Given a list of keypress instructions will emulate them on the SUT.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def keypress_get_generator(self):
        """ Return a generator to convert files to keypresses """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def power_on(self):
        """ Turn power on """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def power_off(self):
        """ Turn power off """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def power_shutdown(self):
        """ Nice shutdown of machine """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def power_reset(self):
        """ Reset power """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def power_reboot(self):
        """ Reboot the machine  """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    def power_status(self):
        """ Get power status of machine """
        raise NotImplementedError("ERROR: Unimplemented function.")