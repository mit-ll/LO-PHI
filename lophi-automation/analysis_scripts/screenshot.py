"""
    This contains a class to start an analysis using the specified modules and 
    the specified machine.
    
    (c) 2015 Massachusetts Institute of Technology
"""
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G
from lophi_automation.analysis_scripts import LophiAnalysis


class ScreenshotAnalysis(LophiAnalysis):
    """
        Simple screenshot example
    """

    # These are required to automatically find an appropriate machine for the
    # analysis
    NAME = "screenshot"
    DESCRIPTION = "Simple screenshot test"
    MACHINE_TYPE = G.MACHINE_TYPES.PHYSICAL
    VOLATILITY_PROFILE = "WinXPSP3x86"

    def analysis_start(self):
        """
            Simply take a screenshot
        """

        # Analysis is done after this function returns
        self.CONTINUE_EXECUTION = False
        
        # Extract some important variables
        machine = self.machine

        memory_file = "memory_dump.mfd"
        # Take another memory dump
        print "* %s: Dumping memory..."%self.machine.config.name
        if not machine.memory_dump(memory_file):
            raise "Bad memory read."
        
        vol_uri = "file://"+memory_file
        # Let's take a screenshot
        try:
            print "* Taking a screenshot."
            screenshot_file = "sut_screenshot"
            self.machine.screenshot(screenshot_file,vol_uri=vol_uri)
        except:
            logger.error("Could not take a screenshot.")
            pass