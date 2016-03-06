#!/usr/bin/python
"""
    Example script for bridging the semantic gap from
    SATA -> Disk actions -> File system activity

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import os
import sys
import argparse
import time
import multiprocessing
import subprocess
import logging
logger = logging.getLogger(__name__)


# LOPHI
import lophi.globals as G
from lophi.data import DiskSensorPacket
from lophi.capture import CaptureReader
from lophi.dataconsumers.logger import LoPhiLogger
from lophi_semanticgap.disk.sata import SATAInterpreter
from lophi_semanticgap.disk.sata_reconstructor import SATAReconstructor, PhysicalPacket
from lophi_semanticgap.disk.filesystem_reconstructor import SemanticEngineDisk


# Defaults
default_dest_ip = "172.20.1.2"    


## ========================================
## Code to do real-time analysis of
## the live cap
##

class Analyze(multiprocessing.Process):
    """
        This class will take a dcap file as input and output nicely formatted 
        data.
    """

    def __init__(self, 
                 dcap_filename, 
                 disk_img, 
                 output_queues, 
                 tail_enable=False,
                 sensor_type=G.MACHINE_TYPES.PHYSICAL
                 ):
        """
            Store our input variables for later.
        """
        self.dcap_filename = dcap_filename
        self.disk_img = disk_img
        self.output_queues = output_queues
        self.tail_enable = tail_enable
        self.sensor_type = sensor_type
        
        self.output_dir = "/".join(dcap_filename.split("/")[:-1])

        multiprocessing.Process.__init__(self)

    def run(self):
        """
            This function will read a raw disk capture and use a scanned disk 
            image to reconstruct the recorded SATA traffic and output the 
            semantic output.
        """

        # copy our disk image to a temporary working image
        self.working_disk_img = os.path.join(self.output_dir, "disk.img.tmp")
        print "* Creating temporary working image from disk scan. (%s)"%self.working_disk_img
        
        # Delete, copy, chmod new file
        try:
            os.unlink(self.working_disk_img)
        except:
            pass
        cmd = "cp --sparse=always %s %s" % (self.disk_img, self.working_disk_img)
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        os.chmod(self.working_disk_img, 0755)

        # Set up our semantic bridge
        print "* Parsing disk image %s into our semantic engine... (This may take a while)" % self.working_disk_img
        semantic_engine = SemanticEngineDisk(self.working_disk_img)
  
        # Start processing our dcap
        print "* Processing dcap file %s..." % self.dcap_filename
        # SATA Interpreter
        sata = SATAInterpreter()  
        """
            @TODO Extract sector size from PyTSK
        """
        sata_reconstructor = SATAReconstructor(sector_size=G.SENSOR_DISK.DEFAULT_SECTOR_SIZE)
    
        # read from the cap file in real time
        reader = CaptureReader(self.dcap_filename)

        # Tailing or terminating?
        reader_iter = reader
        if self.tail_enable:
            reader_iter = reader.tail()

        # Loop over all of the dcap contents
        for (timestamp, data) in reader_iter:
            
            if self.sensor_type == G.MACHINE_TYPES.PHYSICAL:
                (header, data) = sata.extract_sata_data(data)

                # deal with SATA NCQ reordering
                disk_sensor_pkts = sata_reconstructor.process_packet(PhysicalPacket(header, data))
            else:
                disk_sensor_pkts = [DiskSensorPacket(data)]
        
            # Process all of our disk packets
            if disk_sensor_pkts:
                for dsp in disk_sensor_pkts:
                    # Skip empty packets
                    if not dsp:
                        continue
      
                    try:
                        fs_operations = semantic_engine.get_access(dsp.sector, 
                                                                   dsp.num_sectors, 
                                                                   dsp.disk_operation, 
                                                                   dsp.data)   
                        self.log_output(timestamp, fs_operations)                   
                               
                    except:
                        logging.exception("Encountered error while trying to bridge semantic gap for this disk access.")



    def log_output(self, timestamp, fs_operations):
        """
            This function will take in a list of actions from
            our semantic engine and output it to all of our output queues
        
            @param timestamp: timestamp associated with these actions
            @param fs_operations: list of filesystem operations from our 
                    semantic engine
        """
    
        # Anything new happen?
        if not fs_operations:
            return

        # aggregate actions since we do it sector by sector
        actions = []
        current_action = None
        last_sector = 0
        for fs_op in fs_operations:
        
            if not current_action:
                current_action = fs_op
                last_sector = current_action['sector']
                continue
        
            # check if this fs_op has the same inode and consecutive sector
            if ((fs_op['inode'] == current_action['inode']) and
                (fs_op['sector'] == last_sector + 1)):
            
                # aggregate the data and continue
                current_action['raw_data'] = current_action['raw_data'] + fs_op['raw_data']
                last_sector += 1
            
                #print "Aggregating inode %s, file %s, sector %d" % (str(fs_op['inode']), fs_op['filename'], fs_op['sector'])
            
            
            else:
                # otherwise, add the current_action to our list of actions and
                # start a new current_action based on fs_op
                actions.append(current_action)
                current_action = fs_op
                last_sector = current_action['sector']
            
        # make sure that the last current_action got added
        actions.append(current_action)


        # Setup our output dictionary to pass back to our aggregator
        output = {}
        
        # Package for log file
        output['MODULE'] = "LOPHI"
        #output['MACHINE'] = "JADOCS"
        #output['PROFILE'] = "WinXPSP3x86"
        #output['PROFILE'] = "Win7"        
        output['SENSOR'] = "disk"
    
        # Append timestamp
        for a in actions:
            a["Timestamp"] = timestamp
            a["Content"] = ""
    
        # Header and data
        #  {'sector':sector, 'op':op, 'op_type':op_type, 'inode':mft_record_no, 'filename':filename, 'raw_data':raw_data, 'semantic_data':semantic_data}
        #output['HEADER'] = ['Timestamp','Operation','Filename','Content']
        output['HEADER'] = ['Timestamp','Operation','Filename','Sector','Inode','Semantic Data']
    
        out_data = []
    
        # Output each action
        for action in actions:

            filename = ""
            original_path = ""
            # Debug info
            if action['filename'] is None:
                logger.debug("NOP")
            else:
                logger.debug("%s: %s" % (action['op_type'], action['filename']))

            semantic_data = None

            # Append to output    
            out_data.append([action['Timestamp'],
                             action['op_type'],
                             action['filename'],
                             action['sector'],
                             action['inode'],
                             ""
                             ])
            
            if action['semantic_data'] is not None:
                for sd in action['semantic_data']:
                    if len(sd['changes']) > 0:
                        for change in sd['changes']:
                            
                            meta_old = str(sd['changes'][change]['old'])
                            meta_new = str(sd['changes'][change]['new'])
                            
                            if change == "atime" or change == "mtime" or change == "ctime" or change == "crtime":
                                meta_old = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                         time.localtime(sd['changes'][change]['old']))
                                meta_new = time.strftime('%Y-%m-%d %H:%M:%S', 
                                                         time.localtime(sd['changes'][change]['new']))
                            
                            out_data.append([action['Timestamp'],
                                         "["+change.upper()+" MODIFIED]",
                                         sd['filename'],
                                         action['sector'],
                                         meta_old + " -> " + meta_new
                                         ])
                        

        output['DATA'] = out_data
    
        for q in self.output_queues:
            q.put(output)
            
        for out in out_data:
            if out[2] != "unknown":
                if isinstance(out[4],dict):
                    print "%s %s"%(out[1],out[2])
                else:
                    print "%s %s %s"%(out[1],out[2], out[4])




def main(options):

    # Setup our log files 
    dcap_filename = options.dcap_file
    # Our output will just be the same filename with a CSV extension
    (base_name, ext) = os.path.splitext(dcap_filename)
    log_csv_filename = base_name +".csv"
    
    # create csv logger
    log_csv_queue = multiprocessing.Queue()
    log_csv_writer = LoPhiLogger(log_csv_queue, 
                             filename=log_csv_filename,
                             filetype="csv")
    log_csv_writer.start()
    
    # start real-time analysis
    print "* Storing output in %s" % log_csv_filename
    analysis_process = Analyze(dcap_filename,
                                options.disk_img,
                                [log_csv_queue],
                                tail_enable=options.tail_enable,
                                sensor_type=options.sensor_type)

    analysis_process.run()
    
    log_csv_writer.terminate()


if __name__ == "__main__":
    # Get our machine types
    machine_types = {}
    for x in G.MACHINE_TYPES.__dict__:
        if x != "ASCII" and not x.startswith("_"):
            machine_types[x] = G.MACHINE_TYPES.__dict__[x]
            
    # Import our command line parser
    parser = argparse.ArgumentParser()
 
    # Capture type
    parser.add_argument("-T", "--type", action="store", type=int,
        dest="sensor_type", default=0,
        help="Type of sensor. %s"%machine_types)
 
    # Scan file
    parser.add_argument("-s", "--disk_img", action="store", dest="disk_img",
                        default=None, 
                        help="Scanned disk image filename. (e.g. disk.img)")
 
    # Directory where we store output
    parser.add_argument("-i", "--dcap_file", action="store", dest="dcap_file", 
                        default=None, 
                        help="Filename of a disk capture file. (e.g. lophi_disk_capture.dcap")
 
    # Tail or offline analysis?
    parser.add_argument("-t", "--tail", action="store_true", dest="tail_enable", 
                        default=False, 
                        help="Continuing tailing file. (Useful for live analysis)")
    
    # Debug
    parser.add_argument("-d", "--debug", action="store_true", help="Enable DEBUG")
     
    # Get arguments
    options = parser.parse_args()
    
    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
        
    # Make sure that a disk image was given
    if options.disk_img is None:
        logger.error("Please specify a disk scan image file.")
        parser.print_help()
        sys.exit(-1)
    elif not os.path.exists(options.disk_img):
        logger.error("Disk image file does not exist. (%s)"%options.disk_img)
        parser.print_help()
        sys.exit(-1)
        
    # Make sure a dcap was given
    if options.dcap_file is None:
        logger.error("Please specify a disk capture file.")
        parser.print_help()
        sys.exit(-1)
    elif not os.path.exists(options.dcap_file):
        logger.error("Disk capture file does not exist. (%s)"%options.dcap_file)
        parser.print_help()
        sys.exit(-1)
 
     
    main(options)



