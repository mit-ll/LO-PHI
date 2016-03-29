"""
    This contains all of the classes for specific types of analysis

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import logging
import multiprocessing
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G

class AnalysisEngine:
    """
        Abstract class used to implement all of our analysis
    """
    
    analysis_id = 0
    def __init__(self):
        """
            Ensure this class is never used directly
        """
        # Ensure that this class is never initialized
        if self.__class__ == AnalysisEngine:
            raise("Abstract class initialized directly!")
        
        self.id = AnalysisEngine.analysis_id
        AnalysisEngine.analysis_id += 1
        
        self.analysis_engine = None
        
        
    def start(self):
        """
            Start the specified analysis
        """
        raise NotImplementedError("ERROR: Unimplemented function.")    
    
    def __del__(self):
        if self.analysis_engine is not None:
            logger.debug("Killing analysis before exiting.")
            # Use try because it may already be dead
            try:
                self.analysis_engine.terminate()
                self.analysis_engine.join()
            except:
                pass
        
    def stop(self):
        """
            Stop our analysis by killing the spawned process
        """
        if self.analysis_engine is None:
            logger.error("No analysis has been started.")
            return
        
        logger.debug("Killing analysis engine process...")
        self.command_queue.put(G.CTRL_CMD_STOP)
        
        # Join process to wait for closure
        self.analysis_engine.join(5)
        
        self.analysis_engine = None
        
    def pause(self):
        """
            This will temporarily pause our analysis
        """
        if self.analysis_engine is None:
            logger.error("No analysis has been started.")
            return
        
        logger.debug("Pausing analysis engine...")
        self.command_queue.put(G.CTRL_CMD_PAUSE)
        
        
    def resume(self):
        """
            Resume a previously paused analysis
        """
        if self.analysis_engine is None:
            logger.error("No analysis has been started.")
            return
        
        logger.debug("Resuming analysis engine...")
        self.command_queue.put(G.CTRL_CMD_UNPAUSE)




class LoPhiAnalysisEngine(AnalysisEngine):
    
    
    def __init__(self,running_dict=None,services_host=G.RabbitMQ.AMQP_HOST):
        """
            Initialize our analysis engine
        """
        # Save the amqp host that this analysis engine will use.
        self.services_host = services_host
        
        # Save our shared dict of running processes
        self.running_dict = running_dict
        
        self.analysis_engine = None
        
        AnalysisEngine.__init__(self)


    def start(self, 
              AnalysisClass, 
              lophi_command=None, 
              machine=None, 
              machine_list=None,
              machine_name=None,
              machine_queue=None):
        """
            Start our analysis using the class that was passed in as an argument
        """
        
        # Setup a queue to communicate with the process
        self.command_queue = multiprocessing.Queue()
        
        # Initialize our analysis
        self.analysis_engine = AnalysisClass(self.command_queue,
                                             lophi_command=lophi_command,
                                             services_host=self.services_host,
                                             machine=machine,
                                             machine_name=machine_name,
                                             machine_queue=machine_queue,
                                             machine_list=machine_list,
                                             running_dict=self.running_dict,
                                             lophi_analysis_id=self.id)
        if self.analysis_engine is None:
            logger.error("Analysis could not be started.")
            return False
        
        # Spawn a new proccess
        self.analysis_engine.start()
        
        return True



class DiskAnalysisEngine(AnalysisEngine):
    """
        This small class serves as our analysis engine for disk analysis
    """
    
    
    
    def __init__(self, 
                 machine, 
                 output_queue):
        """
            Initialize our disk analysis
            
            @param machine: Machine object that we will be performing analysis on
            @param output_queue: Queue that resulting data will be returned on
        """
        
        if machine.disk is None:
            logger.error("Machine (%s) does not have a disk sensor associated with it to use for analysis."%machine.config.name)
            return None
        
        # set our variables for later
        self.machine = machine
        self.output_queue = output_queue
        
        # Initialize the analysis engine
        self.analysis_engine = None
        
        AnalysisEngine.__init__(self)
        
        
    def start(self):
        """
            Start our analysis by spawning a new process that will bridge the
            semantic gap for disk accesses
        """
        from lophi_semanticgap.disk import DiskEngine
        
        # Setup a queue to communicate with the process
        self.command_queue = multiprocessing.Queue()
        
        # Connect to our disk sensor
        self.machine.disk._connect()
        
        # Initialize our Volatility wrapper
        self.analysis_engine = DiskEngine(self.machine,
                                           self.command_queue,
                                           self.output_queue)
        if self.analysis_engine is None:
            logger.error("Analysis could not be started.")
            return
        
        # Spawn a new proccess
        logger.debug("Starting DiskAnalysisEngine...")
        self.analysis_engine.start()
        
    def stop(self):
        """
            Stop any disk analysis nicely
        """
        logger.debug("Stopping disk analysis.")
        
        # Close our socket for the disk sensor
#         self.machine.disk.sata_disable()
        self.machine.disk._disconnect()
        
        # terminate the analysis (It could be blocking)
        self.analysis_engine.terminate()
    
        # Join process to wait for closure
        self.analysis_engine.join(5)
        
        self.analysis_engine = None
        
        self.command_queue.close()
        
        
class DiskCaptureEngine(DiskAnalysisEngine):
    
    def start(self):
        """
            Start capturing disk traffic for the specified machine 
        """
        
        from lophi_semanticgap.disk import DcapEngine
        
        # Setup a queue to communicate with the process
        self.command_queue = multiprocessing.Queue()
        
        try:
            # Connect to our disk sensor
            self.machine.disk._connect()
            
            # Initialize our Volatility wrapper
            self.analysis_engine = DcapEngine(self.machine,
                                                 command_queue=self.command_queue, 
                                                 output_queue=self.output_queue)
            
            if self.analysis_engine is None:
                logger.error("Analysis could not be started.")
                return
            
            # Spawn a new proccess
            logger.debug("Starting DiskCaptureEngine...")
            self.analysis_engine.start()
        except:
            print "Got error!"
            import traceback
            traceback.print_exc()
        


class MemoryAnalysisEngine(AnalysisEngine):
    """
        This small class serves as our analysis engine for memory
    """
    
    def __init__(self, 
                 machine, 
                 output_queue, 
                 plugins=None, 
                 poll_interval=1):
        """
            Initialize our memory analysis
            
            @param machine: Machine object that we will be performing analysis on
            @param output_queue: Queue that resulting data will be returned on
            @param plugins: Volatility plugins that we want to execute
            @param poll_interval: Time between analysis
        """
        
        if machine.memory is None:
            logging.error("Machine (%s) does not have a memory sensor associated with it to use for analysis."%machine.config.name)
            return None
        
        # set our variables for later
        self.machine = machine
        self.output_queue = output_queue
        self.poll_interval = poll_interval
        
        from lophi_semanticgap.memory import MODULES_DICTIONARY
        
        # Figure out what plugins we are using
        if plugins is not None:
            self.plugins = plugins
        elif machine.config.volatility_profile in MODULES_DICTIONARY:
            logger.warn("No memory plugins specified.  Defaulting to base set.")
            self.plugins = MODULES_DICTIONARY[machine.config.volatility_profile]
        else:
            logger.error("No memory plugins were specified, and no default plugins could be found for %s."%machine.config.volatility_profile)
            return False
        
        # Initialize the analysis engine
        self.analysis_engine = None
        
        AnalysisEngine.__init__(self)
        
        
    def start(self):
        """
            Start our analysis by spawning a new process that will poll memory
            at a fixed interval.
        """
        from lophi_semanticgap.memory import VolatilityEngine
        
        # Setup a queue to communicate with the process
        self.command_queue = multiprocessing.Queue()
        
        # Initialize our Volatility wrapper
        self.analysis_engine = VolatilityEngine(self.machine,
                                                 self.plugins,
                                                 self.command_queue,
                                                 self.output_queue,
                                                 poll_interval=self.poll_interval)
        if self.analysis_engine is None:
            logger.error("Analysis could not be started.")
            return
        
        # Spawn a new proccess
        self.analysis_engine.start()
        
        
        
class NetworkCaptureEngine(AnalysisEngine):
    
    def __init__(self,machine, output_queue):
        """
            Initialize our network capture engine
        """
        self.machine = machine
        self.output_queue = output_queue
        
        AnalysisEngine.__init__(self)
        
    def start(self):
        """
            Start capturing network traffic for the specified machine 
            (interface)
        """
        
        from lophi.sensors.network import NetworkCapture
        
        # Setup a queue to communicate with the process
        self.command_queue = multiprocessing.Queue()
        
        # Initialize our Volatility wrapper
        self.analysis_engine = NetworkCapture(self.machine,
                                             command_queue=self.command_queue, 
                                             output_queue=self.output_queue)
        
        if self.analysis_engine is None:
            logger.error("Analysis could not be started.")
            return
        
        # Spawn a new proccess
        self.analysis_engine.start()
        
    def stop(self):
        """
            Stop any network analysis nicely
        """
        logger.debug("Stopping network analysis.")
        self.analysis_engine.stop()

        # terminate the analysis (It could be blocking)
#         self.analysis_engine.terminate()
    
        # Join process to wait for closure
        self.analysis_engine.join(5)
        
        self.analysis_engine = None
        
        self.command_queue.close()
