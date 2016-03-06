"""

    (c) 2015 Massachusetts Institute of Technology
"""
class LophiConfig:
    
    def _get_option(self,Config, name, option):
        """
            Check to see if an option exists and set it as a class variable
        """
        if Config.has_option(name, option):
            self.__dict__[option] = Config.get(name, option)
            return True
        else:
            self.__dict__[option] = None
            return False