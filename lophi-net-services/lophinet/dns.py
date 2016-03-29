"""
    Adapted code to host a simple DNS server

    Reference: http://code.activestate.com/recipes/491264-mini-fake-dns-server/

    (c) 2015 Massachusetts Institute of Technology
"""

import socket
import multiprocessing
import logging
logger = logging.getLogger(__name__)

DNS_PORT = 53

class DNSQuery:
    def __init__(self, data):
        self.data=data
        self.domain=''
        
        type = (ord(data[2]) >> 3) & 15   # Opcode bits
        if type == 0:                     # Standard query
            ini=12
            lon=ord(data[ini])
            while lon != 0:
                self.domain+=data[ini+1:ini+lon+1]+'.'
                ini+=lon+1
                lon=ord(data[ini])

    def response(self, ip):
        packet=''
        if self.domain:
            packet+=self.data[:2] + "\x81\x80"
            packet+=self.data[4:6] + self.data[4:6] + '\x00\x00\x00\x00'   # Questions and Answers Counts
            packet+=self.data[12:]                                         # Original Domain Name Question
            packet+='\xc0\x0c'                                             # Pointer to domain name
            packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
            packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.'))) # 4bytes of IP
        return packet


class DNSServer(multiprocessing.Process):
    
    def __init__(self,dns_lookup_table):
        """
            Initialize our DNS Server
        """
        self.dns_lookup_table = dns_lookup_table
       
        multiprocessing.Process.__init__(self)
        
    def run(self):
        """
            Open our listening socket
        """
        logger.info("Starting LO-PHI DNS Server...")
        
        try:
            udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udps.bind(('',DNS_PORT))
        except:
            logger.error("Could not bind to port %d.  (Are you root?)"%DNS_PORT)
            return
        
        while True:
            # Get our raw data
            data, addr = udps.recvfrom(1024)
            # Process the DNS Query
            p=DNSQuery(data)
            
            logger.debug("Got request for '%s'"%p.domain)
            
            # See if we have an entry for that
            if p.domain in self.dns_lookup_table:
                ip = self.dns_lookup_table[p.domain]
                udps.sendto(p.response(ip), addr)
            
                logger.info('Resolved: %s -> %s' % (p.domain, ip))
            else:
                logger.info('Had no response.')
  
  
  
