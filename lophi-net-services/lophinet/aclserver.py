"""
    Access-control server to add machines to PXE boot

    (c) 2015 Massachusetts Institute of Technology
"""
from multiprocessing import Process
import socket
import sys
import time
import logging
logger = logging.getLogger(__name__)

import lophinet.globals as G



class ACLServer(Process):
    """
        This is our access-control server used to temporarily allow MAC 
        addresses to PXE boot
        
        @TODO: Validate entries and return responses!
    """
    def __init__(self, acl, mac_to_ip, mac_to_pxe_conf, address="0.0.0.0", port=G.PXE_ACL_PORT):
        Process.__init__(self)
        
        # Keep our mappings
        self.acl = acl
        self.mac_to_ip = mac_to_ip
        self.mac_to_pxe_conf = mac_to_pxe_conf
        self.RUNNING = True
    
        # Where to listen?
        self.addr = address
        self.port = port
    
    def process_acl_request(self, data, conn):       
        """
            Process our ACL requests and modify the appropriate shared objects.
        """
        # get our parts
        #data, addr = request
        
        cmd = data.split(" ")
        
        # Add MAC to ACL?
        if cmd[0] == G.PXE_ADD_ACL:
            mac_addr = cmd[1].lower()
            self.acl[mac_addr] = True
            
            logger.info('Added mac address ' + mac_addr + ' to the acl.')
            return
        
        # Delete MAC from ACL?
        if cmd[0] == G.PXE_DEL_ACL:
            mac_addr = cmd[1].lower()
            if mac_addr in self.acl:
                del self.acl[mac_addr]
                
            logger.info('Removed mac address ' + mac_addr + ' from the acl.')       
            return

        # Resolve and IP from a MAC address
        if cmd[0] == G.PXE_GET_IP:
            mac_addr = cmd[1].lower()
            logger.info('Received Address Lookup Request for %s' % mac_addr)
            
            resp = None
            if mac_addr in self.mac_to_ip:
                resp = ".".join(map(str,self.mac_to_ip[mac_addr]))
            else:
                resp = G.PXE_NO_IP_RESP

            conn.send(resp)
            logger.info('Responded to Address Lookup Request for %s with %s' % (mac_addr, resp))

        # Set a custom PXE config file
        if cmd[0] == G.PXE_SET_CONF:
            mac_addr = cmd[1].lower()
            conf_file = cmd[2]
            
            self.mac_to_pxe_conf[mac_addr] = conf_file
            
            logger.info('Set ' + mac_addr + ' to boot from \'%s\''%conf_file)       
            return
            
            
            
    
    def run(self):

        logger.info("Starting up ACL Server on port %d" % self.port)

        # Our address to listen on
        addr = (self.addr, self.port)

        # Open our socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind to our address/port
        BOUND = False
        while not BOUND:
            try:
                sock.bind(addr)
                BOUND = True
            except:
                logger.error("Cannot bind socket... (Retrying in %d seconds)" % 10)
                time.sleep(10)


        while self.RUNNING:
            sock.listen(5)
            conn, addr = sock.accept()
            
            # Read our command message
            try:
                msg = conn.recv(512)
                self.process_acl_request(msg,conn)
                conn.close()
            except:
                logger.error("Problem processing request.")
                G.print_traceback()
            

        # Close up shop
        sock.close()


        # Sleep for a few seconds, then kill everything
        logger.info("Shutting down ACL server...")

        sys.exit(0)
        
        
