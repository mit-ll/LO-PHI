"""
    Basic helper functions for dealing with configuration files

    (c) 2015 Massachusetts Institute of Technology
"""
import ConfigParser
import logging
import os
import sys
import importlib
logger = logging.getLogger(__name__)

# LO-PHI

# Globals
import lophi.globals as  G
from lophi.machine.physical import PhysicalMachine
from lophi.sensors.disk.physical import DiskSensorPhysical
from lophi.sensors.control.physical import ControlSensorPhysical
from lophi.sensors.cpu.physical import CPUSensorPhysical
from lophi.sensors.memory.physical import MemorySensorPhysical
from lophi.sensors.network.physical import NetworkSensorPhysical

# LO-PHI Automation
from lophi_automation.configs.machineconfig import MachineConfig
from lophi_automation.configs.controllerconfig import ControllerConfig

def extract_analysis(module):
    """
        Simple function to extract our analysis from an imported module
        
        @param module: module name to extract analysis class from
        @return: Subclass of LophiAnalysis used for analysis
    """
    import inspect
    from lophi_automation.analysis_scripts import LophiAnalysis
     
    analysis_modules = []
    
    # Scall all imported objects
    for a in module.__dict__:
        var = module.__dict__[a]
        
        # See if its a class that is a strict subclass of LophiAnalysis
        if  inspect.isclass(var):
            if issubclass(var,LophiAnalysis) and var != LophiAnalysis:
                if var not in analysis_modules:
                    analysis_modules.append(var)
                    
    # Enforce 1 analysis per file
    if len(analysis_modules) > 1:
        logger.error("Found more than 1 analysis class in %s"%module)
        return None
    elif len(analysis_modules) == 0:
        logger.warning("Module (%s) has no analysis class in it."%module)
    else:
        return analysis_modules[0]


def import_analysis_scripts(path):
    """
        This is used to import analysis script files and extract their classes.
        
        @path: Directory on the disk that contains module files that all
                contain subclasses of LophiAnalysis
                
        @return: dict of analysis classes (dict[name] = Class)
    """
    
    # Append this path to import from it
    sys.path.append(path)
    
    analysis_classes = {}
    # scan our path for suitable modules to import
    if os.path.exists(path) and os.path.isdir(path):
        for dirpath, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith(".py") and not filename.startswith("_"):
                    
                    # get our full filename
                    path_filename = os.path.join(dirpath,filename)
                    
                    # get our module name
                    split_path = dirpath.split(os.path.sep)
                    module = '.'.join(split_path)
                    
                    module = filename[:-3]
                    
                    logger.debug("Extracting analyses from %s..."%module)
    
                    try:
                        tmp_module = importlib.import_module(module)
                        analysis = extract_analysis(tmp_module)
                    except:
                        logger.error("Could not import module: %s"%module)
                        G.print_traceback()
                        continue
                    
                    if analysis is not None:
                        if "NAME" in analysis.__dict__:
                            analysis_classes[analysis.NAME] = (analysis,path_filename)
                        else:
                            logger.warning("Found analysis with no NAME attribute")
                            analysis_classes[analysis.__class__.__name__] = (analysis,path_filename)
                            
        return analysis_classes



def import_from_config(config_file, config_type=None):
    """
        This will import our config file into a LoPhiConfig or Machine class 
        for each item in the config
        
        This is only done for physical machines.  Virtual machines are handled
        by libvirt.
        
        @param config_file: Config file on disk
        @param config_type: Type of config file to parse
                        controller, machine, sensor
        @return: List of classes of the appropriate type in dictionary 
                referenced by their name
    """
    if config_type is None:
        logger.error("ERROR: Must specify type of config to import.")
        return None

    Config = ConfigParser.ConfigParser()
    Config.read(config_file)

    config_list = {}
    for config in Config.sections():
        name = config

        logging.debug("Intializing config for %s..." % name)

        config = None

        if config_type == "machine":
            # Create our config
            config = MachineConfig(name, Config)

            # What type of machine?
            config_list[name] = PhysicalMachine(config)

        elif config_type == "controller":
            config = ControllerConfig(name, Config)
            config_list[name] = config

        elif config_type == "sensor":
            # These will only be physical sensors
            # Virtual sensors are all derived from the VM name
            
            sensor_type = int(Config.get(name, "type"))
            if sensor_type == G.SENSOR_TYPES.NETWORK:
                interface = Config.get(name, "interface")
            else:
                sensor_ip = Config.get(name, "ip")
                sensor_port = int(Config.get(name, "port"))

            if sensor_type == G.SENSOR_TYPES.CONTROL:
                config_list[name] = ControlSensorPhysical(sensor_ip,sensor_port,name=name)
            elif sensor_type == G.SENSOR_TYPES.DISK:
                config_list[name] = DiskSensorPhysical(sensor_ip,sensor_port,name=name)
            elif sensor_type == G.SENSOR_TYPES.MEMORY:
                config_list[name] = MemorySensorPhysical(sensor_ip,sensor_port,name=name)
            elif sensor_type == G.SENSOR_TYPES.CPU:
                config_list[name] = CPUSensorPhysical(sensor_ip,sensor_port,name=name)
            elif sensor_type == G.SENSOR_TYPES.NETWORK:
                config_list[name] = NetworkSensorPhysical(interface,name=name)
            else:
                logging.error("Unrecognized sensor type. (%d)"%sensor_type)

        elif config_type == "images":
            
            # Setup an empty map
            config_list = {G.MACHINE_TYPES.PHYSICAL:{},
                          G.MACHINE_TYPES.KVM:{},
                          G.MACHINE_TYPES.XEN:{}
                          }
            
            if Config.has_section("physical"):
                for (profile,image) in Config.items("physical"):
                    config_list[G.MACHINE_TYPES.PHYSICAL][profile.lower()] = image 
            
            if Config.has_section("virtual"):
                for (profile,image) in Config.items("virtual"):
                    config_list[G.MACHINE_TYPES.KVM][profile.lower()] = image
                    config_list[G.MACHINE_TYPES.XEN][profile.lower()] = image
                
        else:
            logging.error("Unknown config file. (%s)"%(config_type))
            return None

        logging.debug(config_list)

    return config_list
