"""
    Classes to handle logging

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import time
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G

class LogFile:
    """
        This class will handle all of the writing to files for LO-PHI.  Simply
        initialize with a desired filename and output type, and then just feed
        output data structures.
    """

    def __init__(self,filename,output_type="tsv",reprint_header=False):
        try:
            # Globals
            self.log_init = False # Remember if we need to print the headers
            self.reprint_header = reprint_header
            self.outfd = None
            self.separator = "\t"

            # Open output
            G.ensure_dir_exists(filename)
            self.outfd = open(filename,"a+")
            # Set the proper delimiter
            if output_type == "tsv":
                self.separator = "\t"
            if output_type == "csv":
                self.separator = ","
            if output_type == "space":
                self.separator = " "
            self.reprint_header = reprint_header
        except:
            logger.error("ERROR: Could not open %s for logging output."%filename)
            import traceback
            logger.error(traceback.format_exc())
    
    def append(self,output):
        """
            Given output from a Volatility module, will write to the logfile in 
            the desired format
        """

        if self.log_init is False or self.reprint_header:
            # Insert our new headers in reverse order
            line = self.separator.join(output['HEADER'])
            self.outfd.write(line)
            self.log_init = True
            self.outfd.write("\n")
            
        for row in output['DATA']:
            
            # Convert everything to a string
            row = [str(i) for i in row]
            line = self.separator.join(row)
            self.outfd.write(line)
            self.outfd.write("\n")
            
        self.outfd.flush()
            
    def close(self):
        """
            Simply close our file descriptor
        """
        self.outfd.close()



class LogDataStruct(LogFile):
    """
        This class will ingest DataStruct objects and log them appropriately
    """
    
    def append(self,data_struct,memory_address=None, extra=None):
        """
            Write our data structure to a log file on disk
        """
        
        # Write the header if needed
        
        if self.log_init is False or self.reprint_header:
            keys = [str(x) for x in data_struct.keys()]
            line_list = ["Timestamp"]+keys

            # Was extra Data Provided?
            if extra is not None:
                line_list += extra.keys()
                            
            # Was a memory address provided?
            if memory_address is not None:
                line_list += ["Memory Address"]
                
            line = self.separator.join(line_list)
            self.outfd.write(line)
            self.log_init = True
            self.outfd.write("\n")
        
        # Write the actual data
        values = [str(x) for x in data_struct.values()]
        line_list = [str(time.time())]+values

        # Was extra data provided?
        if extra is not None:
            for k in extra.keys():
                line_list.append(extra[k])
            
        # Was a memory address provided?
        if memory_address is not None:            
            line_list += ["0x%016X"%memory_address]
        
        line = self.separator.join(line_list)
        self.outfd.write(line+"\n")
        
        self.outfd.flush()
        
        