"""

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
"""

import logging
import logging.handlers
import sys
import traceback
import multiprocessing

from proxyconfig import parse_config
from dhcplib.dhcp_network import *
from dhcplib.dhcp_packet import *


class DhcpServerBase(DhcpNetwork,multiprocessing.Process) :
    def __init__(self, listen_address="0.0.0.0", client_listen_port=68,
                 server_listen_port=67) :
        
        DhcpNetwork.__init__(self,listen_address,server_listen_port,client_listen_port)
        
        self.logger = logging.getLogger('proxydhcp')
        #self.logger.setLevel(logging.INFO)
#         self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s ProxyDHCP: %(message)s')  
        self.consoleLog = logging.StreamHandler()
        self.consoleLog.setFormatter(formatter)
        self.logger.addHandler(self.consoleLog)
        if sys.platform == 'win32':
            self.fileLog = logging.FileHandler('proxy.log')
            self.fileLog.setFormatter(formatter)
            self.logger.addHandler(self.fileLog)
        else:
            if sys.platform == 'darwin':
                self.syslogLog = logging.handlers.SysLogHandler("/var/run/syslog")
            else:
                self.syslogLog = logging.handlers.SysLogHandler("/dev/log")
            self.syslogLog.setFormatter(formatter)
            self.syslogLog.setLevel(logging.INFO)
            self.logger.addHandler(self.syslogLog)
        
        try :
            self.dhcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.dhcp_socket.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
            
            self.dhcp_socket_send = self.dhcp_socket
            
            if sys.platform == 'win32':
                self.dhcp_socket.bind((self.listen_address,self.listen_port))
            else:
                # Linux and windows differ on the way they bind to broadcast sockets
#                 ifname = net.get_dev_name(self.listen_address)
#                 self.dhcp_socket.setsockopt(socket.SOL_SOCKET,IN.SO_BINDTODEVICE,ifname+'\0')
    
                # We need to to do a total hack and have one for sending, one for receiving.
                self.dhcp_socket_send = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
                self.dhcp_socket_send.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
            
                self.dhcp_socket.bind(('',self.listen_port))
                self.dhcp_socket_send.bind((self.listen_address,0))
        except socket.error, msg :
            self.log('info',"Error creating socket for server: \n %s"%str(msg))
        
        self.loop = True
        
        multiprocessing.Process.__init__(self)
        
    def run(self):
        while self.loop:
            try:
                self.GetNextDhcpPacket()
            except:
                traceback.print_exc()
        self.log('info','Service shutdown')
    
    def log(self,level,message):
        if level == 'info':
            self.logger.info(message)
        else:
            self.logger.debug(message)
            
class DHCPD(DhcpServerBase):
    
    loop = True
    
    def __init__(self,configfile='proxy.ini',client_port=68,server_port=67,
                 shared_acl=None,
                 shared_map=None):
                
        self.client_port = int(client_port)
        self.server_port = int(server_port)
        self.config = parse_config(configfile)
        DhcpServerBase.__init__(self,self.config['proxy']["listen_address"],self.client_port,self.server_port)
        self.log('info',"Starting DHCP on ports client: %s, server: %s"%(self.client_port,self.server_port))

        #ip_pool
        # start_ip should be something like [192.168.1.100]
        self.start_ip = map(int, self.config['network']["ip_start"].split("."))
        self.pool_size = int(self.config['network']["pool_size"])
        if self.start_ip[3] + self.pool_size >= 255:
            self.log('error', "Defined start ip address and pool size is too big for class C subnet")

        # Shared objects for access control
        self.acl = shared_acl
        self.mac_to_ip = shared_map
        
        # Keep track of what file each mac is booting
        self.mac_to_bootfile = {}
    
        

    def GetFreeIP(self):
        """
           Returns free IP or None if full
        """
        for i in xrange(self.pool_size):
            ip = self.start_ip
            ip[3] += i

            # ipkey should be something like [192,168,1,102]
            
            if ip not in self.mac_to_ip.values():
                return ip

        # Ran out of IPs
        return None



    def HandleDhcpDiscover(self, packet):

        # don't even bother responding if we have run out of addresses
        mac_addr = ":".join(map(self.fmtHex,packet.GetHardwareAddress()))

        # proposed IP address
        prospective_ip = None

        # if this mac_addr already has an IP, just give it the same one
        if mac_addr in self.mac_to_ip:
            prospective_ip = self.mac_to_ip[mac_addr]
        else:
            # try to find a free IP
            prospective_ip = self.GetFreeIP()

        # if we couldn't get an IP, then throw an error
        if prospective_ip is None:
            self.log('error','No More IPs!  Ignored DHCP Discover from ' + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
            return
        else:
            self.mac_to_ip[mac_addr] = prospective_ip

        # Handle PXE request
        if packet.IsOption('vendor_class_identifier'):
            class_identifier = strlist(packet.GetOption('vendor_class_identifier'))
            if class_identifier.str()[0:9] == "PXEClient":

                
                    
                responsepacket = DhcpPacket()
                responsepacket.CreateDhcpOfferPacketFrom(packet)
                
                # DO ACL check - don't respond for PXE (only) if not in ACL
                if mac_addr not in self.acl:
                    self.log('info','UNAUTHORIZED PXE Discover from ' + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
                    self.log('info', 'Sending bad filename to skip PXE.')
                    self.mac_to_bootfile[mac_addr] = "lophi_no_pxe_access"
                else:
                    self.log('info', 'PXE Booting %s...'%":".join(map(self.fmtHex,packet.GetHardwareAddress())) )
                    # Only permit one boot
#                     del self.acl[mac_addr]
#                     self.logger.info("Deleting %s from acl."%mac_addr)
                    self.mac_to_bootfile[mac_addr] = self.config['proxy']['filename']

                
                responsepacket.SetMultipleOptions( {
                    #'hlen': packet.GetOption("hlen"),
                    #'htype': packet.GetOption("htype"),
                    #'xid': packet.GetOption("xid"),
                    #'flags': packet.GetOption("flags"),
                    'flags': [0,0],
                    'giaddr':[0,0,0,0],
                    'yiaddr':prospective_ip,
                    'ciaddr':[0,0,0,0],
                    'siaddr':self.config['tftp']["address"],
                    'file': map(ord, (self.mac_to_bootfile[mac_addr].ljust(128,"\0"))),
                    'sname': map(ord, "unknown.localdomain".ljust(64,"\0"))
                    } )

                #responsepacket.SetOption("vendor_class_identifier", map(ord, "PXEClient"))
                #if self.config['proxy']['vendor_specific_information']:
                #    responsepacket.SetOption('vendor_specific_information', map(ord, self.config['proxy']['vendor_specific_information']))
                
                responsepacket.SetOption("server_identifier",map(int, self.config['proxy']["listen_address"].split(".")))
                # 1 day
                responsepacket.SetOption("ip_address_lease_time",[0,1,81,128])
                #responsepacket.SetOption("renewal_time_value",[0,255,255,255])
                #responsepacket.SetOption("rebinding_time_value",[0,255,255,255])

                #responsepacket.SetOption("bootfile_name", map(ord, (self.config['proxy']['filename'].ljust(128,"\0"))),)

                #responsepacket.SetOption("subnet_mask",[255,255,255,0])
                responsepacket.SetOption("subnet_mask",map(int, self.config['network']['subnet_mask'].split(".")))
                #responsepacket.SetOption("broadcast_address",[192,168,1,255])
                responsepacket.SetOption("router",map(int, self.config['proxy']["listen_address"].split(".")))
                #responsepacket.SetOption("domain_name_server",map(int, self.config['proxy']["listen_address"].split(".")))
    
                
                self.SendDhcpPacketTo(responsepacket, "255.255.255.255", self.client_port)
                
                self.log('info','******Responded to PXE Discover from ' + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
                
                return

            # Handle normal DHCP
            
            self.log('debug','Noticed a non-boot DHCP Discover packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
            self.log('debug','Responding with normal DHCP Offer packet to '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
            responsepacket = DhcpPacket()
            responsepacket.CreateDhcpOfferPacketFrom(packet)
            responsepacket.SetMultipleOptions( {
                'giaddr':[0,0,0,0],
                'yiaddr':prospective_ip,
                'ciaddr':[0,0,0,0],
                'siaddr':map(int, self.config['proxy']["listen_address"].split("."))
            } )

            responsepacket.SetOption("server_identifier",map(int, self.config['proxy']["listen_address"].split(".")))
            responsepacket.SetOption("ip_address_lease_time",[0,0,0xe,0x10])#[0,255,255,255])
            responsepacket.SetOption("renewal_time_value",[0,0,0x7,0x8])
            responsepacket.SetOption("rebinding_time_value",[0,0,0xc,0x4e])

            responsepacket.SetOption("subnet_mask", map(int, self.config['network']['subnet_mask'].split(".")))
            responsepacket.SetOption("broadcast_address", map(int, self.config['network']['broadcast'].split(".")))
            responsepacket.SetOption("router",map(int, self.config['proxy']["listen_address"].split(".")))
            responsepacket.SetOption("domain_name_server",map(int, self.config['proxy']["listen_address"].split(".")))

            self.SendDhcpPacketTo(responsepacket, "255.255.255.255", self.client_port)
#             self.SendDhcpPacketTo(responsepacket, ".".join([str(x) for x in prospective_ip]) , self.client_port)
            


    def HandleDhcpRequest(self, packet):

        # don't even bother responding if we have run out of addresses
        mac_addr = ":".join(map(self.fmtHex,packet.GetHardwareAddress()))

        # proposed IP address
        prospective_ip = None

        # if this mac_addr already has an IP, just give it the same one
        if mac_addr in self.mac_to_ip:
            prospective_ip = self.mac_to_ip[mac_addr]
        else:
            # try to find a free IP
            prospective_ip = self.GetFreeIP()

        # if we couldn't get an IP, then throw an error
        if prospective_ip is None:
            self.log('error','No More IPs!  Ignored DHCP Discover from ' + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
            return
        else:
            self.mac_to_ip[mac_addr] = prospective_ip

        # Handle PXE request

        if packet.IsOption('vendor_class_identifier'):            
            class_identifier = strlist(packet.GetOption('vendor_class_identifier'))
            if class_identifier.str()[0:9] == "PXEClient":
                
                # Remove the ACL at this point in the protocol
                if mac_addr in self.acl:
                    del self.acl[mac_addr]
                    self.logger.info("Deleting %s from acl."%mac_addr)
                                        
                
                responsepacket = DhcpPacket()
                responsepacket.CreateDhcpAckPacketFrom(packet)
                responsepacket.SetMultipleOptions( {
                    #'hlen': packet.GetOption("hlen"),
                    #'htype': packet.GetOption("htype"),
                    #'xid': packet.GetOption("xid"),
                    'flags': [0,0],
                    'giaddr': packet.GetOption("giaddr"),
                    'yiaddr': prospective_ip,
                    'siaddr': self.config['tftp']['address'],
                    'vendor_class_identifier': map(ord, "PXEClient"),
                    'file': map(ord, (self.mac_to_bootfile[mac_addr].ljust(128,"\0"))),
                    'sname': map(ord, "unknown.localdomain".ljust(64,"\0"))
                } )
            
                responsepacket.SetOption("server_identifier", map(int, self.config['proxy']["listen_address"].split(".")))
                # 1 day
                responsepacket.SetOption("ip_address_lease_time",[0,1,81,128])
                responsepacket.SetOption("subnet_mask", map(int, self.config['network']["subnet_mask"].split(".")))
                #responsepacket.SetOption("broadcast_address",[192,168,1,255])
                responsepacket.SetOption("router",map(int, self.config['proxy']["listen_address"].split(".")))
                #responsepacket.SetOption("domain_name_server",map(int, self.config['proxy']["listen_address"].split(".")))

                
                self.SendDhcpPacketTo(responsepacket, "255.255.255.255", self.client_port)

                self.log('info','****Responded to PXE Request (port 67 ) from ' + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
     
                return

            # Handle Normal DHCP
       
            self.log('debug','Noticed a non PXE DHCP Request (port 67) packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
            
            self.log('debug','Responding with normal DHCP Ack packet to '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
            responsepacket = DhcpPacket()
            responsepacket.CreateDhcpAckPacketFrom(packet)
            responsepacket.SetMultipleOptions( {
                    'giaddr':packet.GetOption('giaddr'),
                    'yiaddr':prospective_ip,
                    'ciaddr':[0,0,0,0],
                    'siaddr':map(int, self.config['proxy']["listen_address"].split("."))
                        } )

            responsepacket.SetOption("server_identifier",map(int, self.config['proxy']["listen_address"].split(".")))
            responsepacket.SetOption("ip_address_lease_time",[0,255,255,255])
            responsepacket.SetOption("renewal_time_value",[0,255,255,255])
            responsepacket.SetOption("rebinding_time_value",[0,255,255,255])

            responsepacket.SetOption("subnet_mask", map(int, self.config['network']['subnet_mask'].split(".")))
            responsepacket.SetOption("broadcast_address", map(int, self.config['network']['broadcast'].split(".")))
            responsepacket.SetOption("router",map(int, self.config['proxy']["listen_address"].split(".")))
            responsepacket.SetOption("domain_name_server",map(int, self.config['proxy']["listen_address"].split(".")))

            self.SendDhcpPacketTo(responsepacket, "255.255.255.255", self.client_port)
            #self.SendDhcpPacketTo(responsepacket, "192.168.1.255", self.client_port)


    def HandleDhcpDecline(self, packet):
        self.log('debug','Noticed a DHCP Decline packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))

        # remove the IP if any was assigned
        mac_addr = ":".join(map(self.fmtHex,packet.GetHardwareAddress()))        
        if mac_addr in self.mac_to_ip:
            del self.mac_to_ip[mac_addr]


    def HandleDhcpRelease(self, packet):
        self.log('debug','Noticed a DHCP Release packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))

        # remove the IP if any was assigned
        mac_addr = ":".join(map(self.fmtHex,packet.GetHardwareAddress()))
        if mac_addr in self.mac_to_ip:
            del self.mac_to_ip[mac_addr]


    def HandleDhcpInform(self, packet):
        self.log('debug','Noticed a DHCP Inform packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))

    def fmtHex(self,input):
        input=hex(input)
        input=str(input)
        input=input.replace("0x","")
        if len(input)==1:
            input="0"+input
        return input

class ProxyDHCPD(DHCPD):
    
    def __init__(self,configfile='proxy.ini',client_port=68,server_port=67):
        self.config = parse_config(configfile)
        self.client_port = client_port
        self.server_port = server_port
        DHCPD.__init__(self,configfile,server_port=server_port)

    def HandleDhcpDiscover(self, packet):
        self.log('debug','Noticed a DHCP Discover packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))
    
    def HandleDhcpRequest(self, packet):
        
        # don't even bother responding if we have run out of addresses
        mac_addr = ":".join(map(self.fmtHex,packet.GetHardwareAddress()))
        
        
        if packet.IsOption('vendor_class_identifier'):
            
            class_identifier = strlist(packet.GetOption('vendor_class_identifier'))
            if class_identifier.str()[0:9] == "PXEClient":
                responsepacket = DhcpPacket()
                responsepacket.CreateDhcpAckPacketFrom(packet)
                responsepacket.SetMultipleOptions( {
                    'hlen': packet.GetOption("hlen"),
                    'htype': packet.GetOption("htype"),
                    'xid': packet.GetOption("xid"),
                    'flags': packet.GetOption("flags"),
                    'giaddr': packet.GetOption("giaddr"),
                    'yiaddr':[0,0,0,0],
                    'siaddr': self.config['tftp']['address'],
                    'file': map(ord, (self.mac_to_bootfile[mac_addr].ljust(128,"\0"))),
                    'vendor_class_identifier': map(ord, "PXEClient"),
                    'server_identifier': map(int, self.config['proxy']["listen_address"].split(".")), # This is incorrect but apparently makes certain Intel cards happy
                    'bootfile_name': map(ord, self.config['proxy']['filename'] + "\0"),
                    'tftp_server_name': self.config['tftp']['address']
                } )
                
                if self.config['proxy']['vendor_specific_information']:
                    responsepacket.SetOption('vendor_specific_information', map(ord, self.config['proxy']['vendor_specific_information']))
                    
                responsepacket.DeleteOption('ip_address_lease_time')
                self.SendDhcpPacketTo(responsepacket, ".".join(map(str,packet.GetOption('ciaddr'))), self.client_port)
                self.log('info','****Responded to PXE request (port 67 ) from ' + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))

    def HandleDhcpDecline(self, packet):
        self.log('debug','Noticed a DHCP Decline packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))

    def HandleDhcpRelease(self, packet):
        self.log('debug','Noticed a DHCP Release packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))

    def HandleDhcpInform(self, packet):
        self.log('debug','Noticed a DHCP Inform packet from '  + ":".join(map(self.fmtHex,packet.GetHardwareAddress())))

    def fmtHex(self,input):
        input=hex(input)
        input=str(input)
        input=input.replace("0x","")
        if len(input)==1:
            input="0"+input
        return input
