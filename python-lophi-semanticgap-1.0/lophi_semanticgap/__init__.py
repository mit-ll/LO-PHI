import logging
logger = logging.getLogger(__name__)

import lophi.globals as G

class SemanticGapEngine:
    """
        Abstract class used to implement a module to bridge a semantic gap.
        e.g. disk, memory
    """
    
    def __init__(self):
        """
            Ensure this class is never used directly
        """
        # Ensure that this class is never initialized
        if self.__class__ == SemanticGapEngine:
            raise("Abstract class initialized directly!")
        
    def start(self):
        """
            Start the specified analysis
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
    
    
    def __del__(self):
        if self.analysis_engine is not None:
            logger.debug("Killing analysis before exiting.")
            self.stop()
            self.analysis_engine.join()
        
    def stop(self):
        """
            Stop our analysis by killing the spawned process
        """
        if self.analysis_engine is None:
            logger.error("No analysis has been started.")
            return
        
        logger.debug("Killing memory analysis process...")
        self.command_queue.put(G.CTRL_CMD_KILL)
        
        self.analysis_engine = None
        
    def pause(self):
        """
            This will temporarily pause our analysis
        """
        if self.analysis_engine is None:
            logger.error("No analysis has been started.")
            return
        
        logger.debug("Pausing memory analysis...")
        self.command_queue.put(G.CTRL_CMD_PAUSE)
        
        
    def resume(self):
        """
            Resume a previously paused analysis
        """
        if self.analysis_engine is None:
            logger.error("No analysis has been started.")
            return
        
        logger.debug("Pausing memory analysis...")
        self.command_queue.put(G.CTRL_CMD_PAUSE)
