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
from lophi_automation.database.db import DatastoreAnalysis, DatastoreSamples

# LO-PHI Semantic Gap
from lophi_semanticgap.memory.volatility_extensions import ButtonClicker

class ButtonExample(LophiAnalysis):
    """
        This script will introspect memory and click buttons
    """

    # These are required to automatically find an appropriate machine for the
    # analysis
    NAME = "buttons"
    DESCRIPTION = "This analysis is used for demonstrating button clicks"
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
        self.CONTINUE_EXECUTION = False
        
        # Extract some important variables
        volatility_profile = self.lophi_command.volatility_profile
        lophi_command = self.lophi_command
        machine = self.machine
        
        sample_doc_id = lophi_command.sample_doc_id
        
        if sample_doc_id is not None:
            # Initialize our database
            DB_samples = DatastoreSamples(self.services_host)
            self.local_path = DB_samples.copy_sample_to_ftp(sample_doc_id)
            remote_path = os.path.relpath(self.local_path, G.FTP_ROOT)
            lophi_command.ftp_info['dir'] = remote_path
        
        print "* Getting a list of current buttons"
        
        if machine.type != G.MACHINE_TYPES.PHYSICAL:
            vol_uri = "vmi://"+machine.config.vm_name
        else:
            vol_uri = "lophi://"+machine.memory.sensor_ip
        
        # Initialize our button clicker instance
        bc = ButtonClicker(vol_uri,
                          machine.config.volatility_profile,
                          machine.memory_get_size(),
                          machine.control)
        
        # Get our current button list
        bc.update_buttons()
        
        # Are we uploading a binary?
        if sample_doc_id is not None:
            # Send keypresses to download binary                     
            print "* Sending keypresses to execute binary..."
            
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
        else:
            print "* No binary provided, you have 10 seconds to open a new window."
            time.sleep(10)
            
        # Click all of the newly created buttons
        print "* Clicking buttons"
        bc.click_buttons(new_only=True)