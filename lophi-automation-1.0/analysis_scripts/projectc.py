"""
    This contains a class to start an analysis using the specified modules and 
    the specified machine.
    
    (c) 2015 Massachusetts Institute of Technology
"""

import multiprocessing
import time
import os
import logging
import tarfile
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G

# LO-PHI Automation
from lophi_automation.analysis_scripts import LophiAnalysis
from lophi_automation.analysis import MemoryAnalysisEngine
from lophi_automation.analysis import DiskAnalysisEngine
from lophi_automation.ext_interface.rabbitmq import LOPHI_RabbitMQ_Producer
from lophi_automation.dataconsumers.datahandler import DataHandler


class GUIDemo(LophiAnalysis):
    """
        This is a sample of a LO-PHI analysis script.  This script will perform
        disk and memory analysis and report it over RabbitMQ until the user
        sends a command to terminate it.
    """

    # These are required to automatically find an appropriate machine for the
    # analysis
    NAME = "projectc"
    DESCRIPTION = "This analysis is used for demoing volatility and TSK modules"
    MACHINE_TYPE = G.MACHINE_TYPES.PHYSICAL
    VOLATILITY_PROFILE = "WinXPSP3x86"
    
 
    
    def analysis_start(self):
        """
            Commands to execute when starting analysis.  Once this returns the
            analysis will wait for commands from the user.
            
            NOTE: Any threads will continue execute until a stop command is
                    received
        """
        
        
        # Analysis is done after this function returns
        self.CONTINUE_EXECUTION = True
        
        # Extract some important variables
        volatility_profile = self.machine.config.volatility_profile
        machine = self.machine
        
        # Create a queue and data handler
        # This enables us to do many to many data flows
        self.data_queue = multiprocessing.Queue()
        self.data_handler = DataHandler(self.data_queue)
    
        # RabbitMQ queue name
        self.rabbitmq = LOPHI_RabbitMQ_Producer(self.services_host,
                                self.data_handler.new_queue(),
                                G.RabbitMQ.SENSOR,
                                exchange_type=G.RabbitMQ.TYPE_FANOUT,
                                exchange=G.RabbitMQ.EXCHANGE_FANOUT)
        # Start data paths
        self.data_handler.start()
        self.rabbitmq.start()
        
    
        # Memory Analysis 
        print "Starting memory analysis..."
        self.mem_analysis = MemoryAnalysisEngine(self.machine,
                                            self.data_queue,
                                            plugins=['pslist'])
        self.mem_analysis.start()
        
        # Disk analysis Analysis 
        print "Starting disk analysis..."
        self.disk_analysis = DiskAnalysisEngine(self.machine,
                                            self.data_queue)
        self.disk_analysis.start()
        
    def analysis_resume(self, args):
        self.mem_analysis.resume()
        self.disk_analysis.resume()
        
    def analysis_pause(self, args):
        self.mem_analysis.pause()
        self.disk_analysis.pause()
        
    def analysis_stop(self, args):
        
        # Stop our analysis
        self.mem_analysis.stop()
        del self.mem_analysis

        self.disk_analysis.stop()
        del self.disk_analysis

        # Then stop data handlers
        self.data_handler.stop()
        self.rabbitmq.stop()
        

    