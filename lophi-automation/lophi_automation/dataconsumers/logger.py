"""
    Very simple process to handle logging of LO-PHI data.
    
    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import logging
logger = logging.getLogger(__name__)
import multiprocessing

# Lo-Phi
import lophi.globals as G
import lophi_automation.protobuf.helper as protobuf
from logfile import LogFile


class LoPhiLogger(multiprocessing.Process):
    """
        This class will continuously read in data from a queue and write to
        the specified log file(s).
    """


    def __init__(self, data_queue, filename=G.DEFAULT_LOG_FILE,
                  filetype="tsv", packed_data=False):
        """
            Initialize our logger to read from a queue and write to files
        """
        # Packed in protobuf or just a dict?
        self.packed_data = packed_data
        
        # Remember our input queue
        self.DATA_QUEUE = data_queue

        # Create our log file        
        self.logfile= LogFile(filename,
                                reprint_header=False,
                                output_type=filetype)


        multiprocessing.Process.__init__(self)

    def run(self):
        """
            Loop forever consuming output from our SUA threads
        """
        # Wait for output to start returning, and handle appropriately
        while True:

            # Get our log data           
            output_packed = self.DATA_QUEUE.get()

            # If its a kill command, just post it
            if output_packed == G.CTRL_CMD_KILL:
                logger.debug("Logger killed...")
                # Close our logs cleanly
                for log in self.logfiles.keys():
                    self.logfiles[log].close()
                break

            if self.packed_data:
                output = protobuf.unpack_sensor_output(output_packed)
            else:
                output = output_packed

            # Log to file
            self.logfile.append(output)

        logger.debug("Logger closed.")


