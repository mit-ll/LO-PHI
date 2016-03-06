import socket
import fcntl
import struct

import netifaces

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def all_interfaces():
    return netifaces.interfaces()

def get_dev_name(ipaddr):
    for netdev in all_interfaces():
        try:
            if get_ip_address(netdev) == ipaddr:
                return netdev
        except:
            pass
        
    return None
