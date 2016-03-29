"""
    Create a pcap file from a given interface
    
    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import logging
logging.basicConfig(level=logging.DEBUG)
import argparse
import multiprocessing

# LO-PHI
from lophi.sensors.network import NetworkSensor
from lophi.capture.network import PcapWriter



def save_pcap(interface, filename):
    """
        Capture network traffic and save it to disk
        
        @param interface: network interface, e.g. eth0
        @param filename: filename to store pcap in
    """
    pcap_out = multiprocessing.Queue()
    pcap_writer = PcapWriter(filename,pcap_out)
    pcap_writer.start()
    net_sensor = NetworkSensor(interface)
    
    while True:
        pkt = net_sensor.read()
        if pkt is None:
            break
        
        pcap_out.put( (pkt[0], str(pkt[1])) )
        
    pcap_out.close()
    pcap_writer.stop()

if __name__ == "__main__":
    
    # Import our command line parser
    args = argparse.ArgumentParser()

    # Add any options we want here
    args.add_argument("-i", "--interface", action="store", type=str,
        dest="interface", default="eth0",
        help="Interface to sniff network traffic from. (Default: eth0)")
    args.add_argument("-o", "--output", action="store", type=str,
        dest="output", default="test.pcap",
        help="Filename to save pcap in. (Default: test.pcap)")
    
    # Get arguments
    options = args.parse_args()
    
    save_pcap(options.interface,options.output)