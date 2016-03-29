"""
    This contains a class to start an analysis using the specified modules and 
    the specified machine.
    
    (c) 2015 Massachusetts Institute of Technology
"""

import multiprocessing
import time
import os

# LO-PHI
import lophi.globals as G

# LO-PHI Automation
from lophi_automation.analysis_scripts import LophiAnalysis
from lophi_automation.analysis import MemoryAnalysisEngine
from lophi_automation.analysis import DiskAnalysisEngine
from lophi_automation.ext_interface.rabbitmq import LOPHI_RabbitMQ_Producer
from lophi_automation.dataconsumers.datahandler import DataHandler
from lophi_automation.database.db import DatastoreSamples

class LoPhiAnalysisJAC(LophiAnalysis):
    """
        This is a sample of a LO-PHI analysis script.  This script will perform
        disk and memory analysis and report it over RabbitMQ until the user
        sends a command to terminate it
    """

    # These are required to automatically find an appropriate machine for the
    # analysis
    NAME = "demo"
    DESCRIPTION = "This analysis does basic memory and disk analysis and sends" \
                  " the output over RabbitMQ"
    MACHINE_TYPE = G.MACHINE_TYPES.PHYSICAL
    VOLATILITY_PROFILE = "WinXPSP3x86"

    def analysis_start(self):
        """
            Commands to execute when starting analysis.  Once this returns the
            analysis will wait for commands from the user.
            
            NOTE: The threads will continue execute until a stop command is
                    received
        """
        # Extract some important variables
        lophi_command = self.lophi_command
        machine = self.machine
        self.sample_doc_id = lophi_command.sample_doc_id
        
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
        
        # Memory Analysis 
        print "Starting memory analysis"
        self.mem_analysis = MemoryAnalysisEngine(self.machine,
                                            self.data_queue,
                                            plugins=['pslist','ssdt'])
        
        # Disk Analysis
        print "Starting disk analysis"
        self.disk_analysis = DiskAnalysisEngine(self.machine,
                                           self.data_queue)
        
        # Start data paths
        self.data_handler.start()
        self.rabbitmq.start()
         
        # Start analysis
        self.mem_analysis.start()
#         self.disk_analysis.start()
    
        # Wait a bit before doing stuff (Allow the OS to finish booting)
        # Also provide time for soundtrack
        time.sleep(5)
                          
        # Copy the sample to the ftp server temporarily so that the SUA can download it
        # store the temp directory name
#         setup_commands=['move %sample% E:\\Incoming', 'E:', 'cd E:\\Incoming', 'pause']
        setup_commands=['pause']
        DB = DatastoreSamples(self.services_host)
        local_path = DB.copy_sample_to_ftp(self.sample_doc_id,commands=setup_commands)
        remote_path = os.path.relpath(local_path, G.FTP_ROOT)
        lophi_command.ftp_info['dir'] = remote_path
                            
        # Get our keypress generator
        kpg = machine.keypress_get_generator()
        
        # Check ftp info, and send commands to execute malware
        if lophi_command.ftp_info['ip'] is not None and lophi_command.ftp_info['dir'] is not None:
            print "* Executing ftp commands..."
            ftp_script = kpg.get_ftp_script(machine.config.volatility_profile,
                                            lophi_command.ftp_info)
            machine.keypress_send(ftp_script)
        else:
            print "* No ftp info given."
         
        
    def analysis_pause(self,args):
        """
            Commands to execute when pausing analysis
        """
        print "* Pausing analysis"
        self.mem_analysis.pause()
#         self.disk_analysis.pause()

    def analysis_resume(self,args):
        """
            Commands to execute when resuming analysis
        """
        print "* Resuming Analysis"
        self.mem_analysis.resume()
#         self.disk_analysis.resume()
        
    def analysis_stop(self,args):
        """
            Commands to execute when stopping analysis
        """
        print "* Stopping analysis"
        # Stop analysis first
        self.mem_analysis.stop()
#         self.disk_analysis.stop()
        # Then stop data handlers
        self.data_handler.stop()
        self.rabbitmq.stop()

        


    