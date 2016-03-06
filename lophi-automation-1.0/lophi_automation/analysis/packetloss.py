"""
    Analysis engine for monitoring packet loss

    (c) 2015 Massachusetts Institute of Technology
"""
# Required packages
# sudo apt-get install python-pypcap python-dpkt 

# Native
import os
import sys
import optparse
import logging
import multiprocessing
import socket
logging.basicConfig()
logger = logging.getLogger(__name__)

# Import 3rd Party libraries
import dpkt, pcap

# Append our system path
sys.path.append(os.path.join(os.getcwd(), "../"))
# LO-PHI
import lophi.globals as G
import lophi.network as NET
# LO-PHI Automation
from lophi_automation.analysis import AnalysisEngine

class PacketlossAnalysisEngine(AnalysisEngine):
    """
        Inter
    """
    
    def __init__(self,interface, sensor_ip):
        """
            Initialize our analysis engine
        """
        # What interface are we analyzing?
        self.interface = interface
        self.sensor_ip = sensor_ip
        
        AnalysisEngine.__init__(self)
        
        
    def start(self):
        """
            Start our analysis using the class that was passed in as an argument
        """
        # Setup a queue to communicate with the process
        self.command_queue = multiprocessing.Queue()
        
        # Setup a shared dictionary to pass results
        manager = multiprocessing.Manager()
        self.return_values = manager.dict()
        
        # Initialize our packet analyzer
        self.analysis_engine = PacketLossAnalyzer(self.interface,
                                                  self.sensor_ip,
                                                  self.return_values)
        
        if self.analysis_engine is None:
            logger.error("Analysis could not be started.")
            return
        
        # Spawn a new proccess
        self.analysis_engine.start()


    def get_results(self):
        """
            Return the results from the shared dictionary
        """
        return dict(self.return_values)


    def stop(self):
        """
            Override our stop function since we are listening on a socket.
            Just kill the process
        """
        if self.analysis_engine is not None:
            # Kill process
            self.analysis_engine.terminate()
            self.analysis_engine.join()
        
            self.analysis_engine = None
        else:
            logger.error("No analysis engine was running.")
        
    
        
        

class PacketLossAnalyzer(multiprocessing.Process):
    
    def __init__(self,interface, sensor_ip, return_values):
        """
            Initialize our packet analyzer process
        """
        
        self.interface = interface
        self.return_values = return_values
        self.sensor_ip = sensor_ip
              
        multiprocessing.Process.__init__(self)
        
    
    def run(self):
        """
            Start our packet capture logging all dropped packets.
            
            In this context we consider a packet to be dropped if we there is 
        """
     
        # Initialize our capture
        pc = pcap.pcap(self.interface)
        pc.setfilter('udp')
        
        # initialize our variables used for comparison
        last_id = None
        sensor_ip_int = socket.inet_aton(self.sensor_ip)
        total_packets = dropped_packets = 0
        # Initialize our dict
        self.return_values['total'] = 0
        self.return_values['dropped'] = 0
        self.return_values['data_received'] = 0
        
        logger.debug("Starting packet capture")
        for ts, pkt in pc:
                
            # Start analyzing our packet
            eth_packet = dpkt.ethernet.Ethernet(pkt)

            

            # We only care about ethernet frames        
            if eth_packet.type != dpkt.ethernet.ETH_TYPE_IP:
                continue
                
            ip_packet = eth_packet.data

            # UDP packet from the IP we are listening too?
            if ip_packet.src == sensor_ip_int and ip_packet.p == dpkt.ip.IP_PROTO_UDP:
                
                    self.return_values['data_received'] += len(eth_packet)
                    
                    total_packets += 1
                    self.return_values['total'] = total_packets
                    
                    # Update the last packet id
                    if last_id is None:
                        last_id = ip_packet.id
                        
                    # packet id be incremental, if it's not, we lost packets
                    elif ip_packet.id > last_id+1:
                        
                        dropped = ip_packet.id - last_id - 1
                        dropped_packets += dropped
                        total_packets += dropped
                        
                        self.return_values['dropped'] = dropped_packets
                        
                        logger.debug("[%f] Dropped packet(s). (%d/%d) (c: %d, p:%d)"%(
                                                                float(dropped_packets)/float(total_packets),
                                                                dropped_packets,
                                                                total_packets,
                                                                ip_packet.id,
                                                                last_id))
                    elif ip_packet.id < last_id and ip_packet.id > 0:
                        dropped = ip_packet.id - 1 + (0xffff - last_id)
                        dropped_packets += dropped
                        total_packets += dropped
                        
                        self.return_values['dropped'] = dropped_packets
                        
                        logger.debug("[%f] Dropped packet(s). (%d/%d) (c: %d, p:%d)"%(
                                                                float(dropped_packets)/float(total_packets),
                                                                dropped_packets,
                                                                total_packets,
                                                                ip_packet.id,
                                                                last_id))
                        
                    # Update our total states
                    last_id = ip_packet.id
                    
            if dropped_packets > total_packets:
                logger.error("DROPPED MORE THAN WE SAW!")
                break



def main(options):
    
    PacketLossAnalyzer
    
        
    
            
        
    
    
    
    
if __name__ == "__main__":
    # Parse arguments
    opts = optparse.OptionParser()

    # Port
    opts.add_option("-i", "--interface", action="store", type="string",
        dest="interface", default=None,
        help="Interface to look for SATA frames on")
    # Destination IP
    opts.add_option("-s", "--sensor_ip", action="store", type="string",
        dest="sensor_ip", default=G.SENSOR_DISK.DEFAULT_IP,
        help="Sensor IP for SATA packets (Default: %s)"%G.SENSOR_DISK.DEFAULT_IP)
    
    # Get arguments
    (options, positionals) = opts.parse_args(None)
    
    
    if options.interface is None:
        logger.error("Please define an interface to sniff.")
        opts.print_help()
        sys.exit(0)
        
    main(options)
    