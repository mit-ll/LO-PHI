"""
    Class for interacting with our PXE server and Access Control

    (c) 2015 Massachusetts Institute of Technology
"""
import socket
import logging
logger = logging.getLogger(__name__)

import lophi.globals as G


class PXEServer:
    
    def __init__(self,ip_address,acl_port=G.PXE_ACL_PORT):
        """
            Intiialize our interface to our PXE server
            
            @param ip_address: IP address of our PXE server
            @param acl_port: Port to communicate to the ACL server on. 
        """
        
        self.ip_address = ip_address
        self.acl_port = acl_port

    def __is_valid_mac(self,mac_address):
        """
            Check to see if the mac address given is a valid MAC format
            
            @param mac_address: MAC address to check
            @return: True/False
            
            @TODO: Implement this? 
        """
        return True
        
    def set_pxe_conf(self, mac_address,pxe_conf):
        """
            Set which PXE configuration this MAC should boot from
            
            @param mac_address: MAC of the system we are adding
            @param pxe_conf: Name of a config to boot clonezilla.  These 
            files are the ones stored in pxelinux.cfg. If not file exists,
            it will scan the samba images directory and auto-generate a config
            if the image exist.
        """
        if not self.__is_valid_mac(mac_address):
            logger.error("Mac address (%s) is an invalid format."%mac_address)
            return False
        
        # add mac address to PXE server ACL
        msg = " ".join([G.PXE_SET_CONF, mac_address, pxe_conf])
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        try:
            sock.connect((self.ip_address, self.acl_port))        
            logger.debug("Sending request to boot %s from %s. (%s:%d)"%(mac_address,
                                                                        pxe_conf,
                                                                        self.ip_address,
                                                                        self.acl_port))            
            sock.send(msg)            
            
        except: # probably get here b/c of socket timeout
            logger.error("Problem sending request to boot %s from %s. (%s:%d)"%(mac_address,
                                                                        pxe_conf,
                                                                        self.ip_address,
                                                                        self.acl_port))            
            
        finally:
            sock.close()

        return True

    def add_mac(self,mac_address):
        """
            Add a MAC address to our access-control list so that the machine 
            will boot from PXE.
            
            @param mac_address: MAC Address to be added to PXE ACL. 
        """
        
        if not self.__is_valid_mac(mac_address):
            logger.error("Mac address (%s) is an invalid format."%mac_address)
            return False
        
        # add mac address to PXE server ACL
        msg = " ".join([G.PXE_ADD_ACL,mac_address])
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        try:
            sock.connect((self.ip_address, self.acl_port))
            logger.debug("Sending request to add %s to %s:%d."%(mac_address,self.ip_address,self.acl_port))
            sock.send(msg)            
            
        except: # probably get here b/c of socket timeout
            logger.error("Problem sending request to add %s to %s:%d."%(mac_address,self.ip_address,self.acl_port))
            sock.close()
            
            return False

        sock.close()

        return True

    def get_ip(self,mac_address):
        """
            Query our DHCP/PXE server to resolve an IP address from a given MAC
            
            @param mac_address: MAC address to lookup at DHCP server 
        """
        
        # Send command to DHCP server
        msg = " ".join([G.PXE_GET_IP,mac_address])
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        # get response
        resp = None
        try:
            sock.connect((self.ip_address, self.acl_port))
            sock.send(msg)
            resp = sock.recv(512)
        except: # probably get here b/c of socket timeout
            pass
        finally:
            sock.close()
        
        if resp is None or resp == G.PXE_NO_IP_RESP:
            logger.error("Failed to get IP address for machine.  PXE Server down? (%s)" % mac_address)
            return None
        else:
            self.ip_addr = resp
            return resp