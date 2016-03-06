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
from lophi_automation.ext_interface.rabbitmq import LOPHI_RabbitMQ_Producer
from lophi_automation.dataconsumers.datahandler import DataHandler
from lophi_automation.database.db import DatastoreAnalysis, DatastoreSamples

class DemoAnalysis(LophiAnalysis):
    """
        This is a sample of a LO-PHI analysis script.  This script will
        continuously power cycle the machine and load a binary on it.
        
        Outputs over RabbitMQ
    """

    # These are required to automatically find an appropriate machine for the
    # analysis
    NAME = "demo2"
    DESCRIPTION = "This analysis is used for our demos"
    MACHINE_TYPE = G.MACHINE_TYPES.PHYSICAL
    VOLATILITY_PROFILE = "WinXPSP3x86"
    
    # Time to run malware
    MALWARE_EXECUTION_TIME = 60*4 # 5 minutes
    
    # Time for OS to boot, before giving up
    OS_TIMEOUT = 60*5 # 5 minutes for the OS to boot

    # Time to wait for OS to stabilize after boot
    OS_BOOT_WAIT = 60
    
    
    def analysis_start(self):
        """
            Commands to execute when starting analysis.  Once this returns the
            analysis will wait for commands from the user.
            
            NOTE: Any threads will continue execute until a stop command is
                    received
        """
        
        
        # Analysis is done after this function returns
        self.CONTINUE_EXECUTION = False
        
        # Extract some important variables
        volatility_profile = self.lophi_command.volatility_profile
        lophi_command = self.lophi_command
        machine = self.machine
        sample_doc_id = lophi_command.sample_doc_id
        db_analysis_id = lophi_command.db_analysis_id
            
        # Initialize our database
        DB_samples = DatastoreSamples(self.services_host)
        DB_analysis = DatastoreAnalysis(self.services_host)
        
        # Copy the sample to the ftp server temporarily so that the SUA can download it
        # store the temp directory name
        # 'sc stop rootkit','sc delete rootkit',
        setup_commands=['start taskmgr']
        local_path = DB_samples.copy_sample_to_ftp(sample_doc_id,commands=setup_commands)
        remote_path = os.path.relpath(local_path, G.FTP_ROOT)
        lophi_command.ftp_info['dir'] = remote_path
        
        
        # Keep retrying in case any step fails
        while True:
            # Make sure that our machine is in the state that we expect.
            # Reversion can fail, make sure we actually revert the disk!
            print "* Resetting machine..."
            machine.power_off()
              
            # Start our machine up
            print "* Powering on machine..."
            machine.power_on()
               
            # Wait for the machine to appear on the network
            print "* Waiting for OS to boot..."
            start = time.time()
            os_timed_out = False
            while not self.machine.network_get_status():
                time.sleep(1)
                if time.time() - start > self.OS_TIMEOUT:
                    os_timed_out = True
                    break
            # Did we timeout?
            if os_timed_out:
                print "** OS boot timeout! (Starting over)"
                continue
                   

            
        
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
                                                plugins=['pslist','ssdt'])
            self.mem_analysis.start()
            
            
            # Wait a bit before doing stuff (Allow the OS to finish booting
            print "* Waiting for the OS to stabilize..."
            time.sleep(self.OS_BOOT_WAIT)
            
            
            # Send keypresses to download binary                     
            print "* Sending keypresses..."
            
            # Get our keypress generator
            kpg = machine.keypress_get_generator()
            
            # Check ftp info, and send commands to execute malware
            if lophi_command.ftp_info['ip'] is not None and lophi_command.ftp_info['dir'] is not None:
                print "* Executing ftp commands..."
                ftp_script = kpg.get_ftp_script(volatility_profile,
                                                lophi_command.ftp_info)
                machine.keypress_send(ftp_script)
            else:
                print "** No ftp info given."
            
                
            # At this the point machine has the binary on it, and is one ENTER key
            # away from executing it.
            
    
            # Run binary for as long as we see fit
            time.sleep(self.MALWARE_EXECUTION_TIME)
            

    


            # Stop our analysis
            self.mem_analysis.stop()
            del self.mem_analysis


            # Then stop data handlers
            self.data_handler.stop()
            self.rabbitmq.stop()
        
            # Wait for things to clean up
            time.sleep(10)
            
            # Turn the machine off
            print "* Shutting down machine..."
            self.machine.power_shutdown()
            
            time.sleep(30)
            
            print "* Done!"
            # Break out of our "try forever" loop
#             break

        # Clean up files on disk
        G.dir_remove(local_path)

    