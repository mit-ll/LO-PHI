"""
    This is a sample script for reading pcap files and outputting source and
    destination pairs.

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import sys
import logging
logger = logging.getLogger(__name__)
import argparse

# 3rd Party
import dpkt

# LO-PHI
from lophi.capture.network import PcapReader
import lophi_semanticgap.network as NET

def get_mac(string):
    
    return "%X:%X:%X:%X:%X:%X" %(ord(string[0]),
                                 ord(string[1]),
                                 ord(string[2]),
                                 ord(string[3]),
                                 ord(string[4]),
                                 ord(string[5]))
    
def get_ip(string):
    
    return "%d.%d.%d.%d"%(ord(string[0]),
                          ord(string[1]),
                          ord(string[2]),
                          ord(string[3]))

def extract_tuples(filename):
    reader = PcapReader(filename)

    rtn_list = []
    other_list = []
    for (ts,pkt) in reader:
        eth = dpkt.ethernet.Ethernet(pkt)
        
        mac_src = get_mac(eth['src'])
        mac_dst = eth['dst']
        
        eth_data = eth['data']
        
        
        # Only parse IPv4
        if eth.type != 2048:
            other_list.append(eth)
            continue
        
        ip = eth.data
        
        ip_src = get_ip(ip['src'])
        ip_dst = get_ip(ip['dst'])
        # Is this TCP?
        if ip.p == 0x6:
            tcp = ip.data
            tcp_sport = tcp['sport']
            tcp_dport = tcp['dport']
            
            logger.debug("TCP: %s:%d -> %s:%d"%(ip_src,
                                                tcp_sport,
                                                ip_dst,
                                                tcp_dport))
            
            rtn_list.append({'protocol':'TCP',
                             'ip_src': ip_src,
                             'ip_dst': ip_dst,
                             'port_src': tcp_sport,
                             'port_dst': tcp_dport})
        # UDP
        elif ip.p == 0x11:
            udp = ip.data
            udp_sport = udp['sport']
            udp_dport = udp['dport']
            
            dns_hosts = []
            if udp_sport == '53' or udp_dport == 53:
                dns = dpkt.dns.DNS(udp.data)
                for q in dns['qd']:
                    dns_hosts.append(q['name'])
                
            logger.debug("UDP: %s:%d -> %s:%d"%(ip_src,
                                                udp_sport,
                                                ip_dst,
                                                udp_dport))
            
            rtn_list.append({'protocol':'UDP',
                             'ip_src': ip_src,
                             'ip_dst': ip_dst,
                             'port_src': udp_sport,
                             'port_dst': udp_dport,
                             'dns':dns_hosts})
        
    return rtn_list, other_list

if __name__ == "__main__":
    
    # Import our command line parser
    args = argparse.ArgumentParser()
 
#     args.add_argument("-t", "--target", action="store", type=str, default=None,
#                       help="Target for control sensor.  (E.g. 172.20.1.20 or VMName)")
    
    # Add any options we want here
    args.add_argument("input_pcap", action="store", type=str, 
                      default=None,
                      help="Pcap file to parse, e.g. test.pcap.")
    
    # Get arguments
    options = args.parse_args()
    
    if options.input_pcap is None:
        args.print_help()
        sys.exit(0)
        
    (recognized,unknown) = extract_tuples(options.input_pcap)
    
    for pkt in recognized:
        port_desc = ""
        if pkt['protocol'] == "UDP" and pkt['port_dst'] in NET.UDP_PORTS:
            port_desc = NET.UDP_PORTS[pkt['port_dst']]
        if pkt['protocol'] == "TCP" and pkt['port_dst'] in NET.TCP_PORTS:
            port_desc = NET.TCP_PORTS[pkt['port_dst']]
            
        if port_desc != "":
            port_desc = "("+port_desc+")"
            
        print "%s: %s:%d -> %s:%d %s"%(pkt['protocol'],
                                    pkt['ip_src'],
                                    pkt['port_src'],
                                    pkt['ip_dst'],
                                    pkt['port_dst'],
                                    port_desc)
        if 'dns' in pkt and len(pkt['dns']) > 0:
            print "  DNS: ", ' '.join(pkt['dns'])
            
            
    print "* Found %d UDP or TCP packets."%len(recognized)
    print "* Found %d packets with unknown protocols."%len(unknown)
    
