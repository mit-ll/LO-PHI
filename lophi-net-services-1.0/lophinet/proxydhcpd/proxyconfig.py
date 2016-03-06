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

import os
import sys
import re
import ConfigParser

class parse_config(dict):
    cp = ConfigParser.ConfigParser()
    def __init__(self,configfile='proxy.ini'):
        if os.access(configfile, os.R_OK) == False:
            print "Unable to read config file: %s" % configfile
            sys.exit(2)
        try:
            self.cp.read(configfile)
        except:
            ConfigParser
            print 'Unable to parse config file: %s' % configfile
            sys.exit(2)
        for section in self.cp.sections():
            if section in ['network']:
                self[section]={}
                for item in self.cp.items(section):
                    self[section][item[0]] = self.cp.get(section,item[0])

            elif section in ['tftp']:
                self[section]={}
                for item in self.cp.items(section):
                    value = self.cp.get(section,item[0])
                    if item[0] == 'address':
                        if self.ipAddressCheck(value):
                            self[section][item[0]] = map(int, value.split("."))
                        else:
                            print valuecheckmsg
                            sys.exit(2)

            # TODO: do better parsing of this section
            elif section in ['proxy', 'pxe']:
                self[section]={}
                for item in self.cp.items(section):
                    value = self.cp.get(section,item[0])
                    valuecheckmsg = 'Please check the value set for ' + item[0] + ' in the ' + section + ' section of ' + configfile
                    if item[0] == 'listen_address':
                        if self.listenAddressCheck(value):
                            self[section][item[0]] = value
                        else:
                            print valuecheckmsg
                            sys.exit(2)
                    elif item[0] == 'dhcp_host':
                        if self.ipAddressCheck(value):
                            self[section][item[0]] = value
                        else:
                            print valuecheckmsg
                            sys.exit(2)
                    elif item[0] in ['filename']:
                        if self.stringCheck(value):
                            self[section][item[0]] = value
                        else:
                            print valuecheckmsg
                            sys.exit(2)
                    elif item[0] in ['vendor_specific_information']:
                        if self.stringCheck(value):
                            self[section][item[0]] = value
                        else:
                            print valuecheckmsg
                            sys.exit(2)
                    else:
                            #print 'The item ' + item[0] + ' in the ' + section + ' section of ' + configfile + ' is unknown'
                            #sys.exit(2)
                        pass
            else:
                #print 'The ' + section + ' section in ' + configfile + ' is unknown'
                #exit(2)
                pass
        

        self['proxy']['client_listen_port'] = "68"
        self['proxy']['server_listen_port'] = "67"
                
    def ipAddressCheck(self,ip_str):
        pattern = r"\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        if re.match(pattern, ip_str):
            return True
        else:
            return False
    
    def listenAddressCheck(self,ip_str):
        if (self.ipAddressCheck(ip_str) or "0.0.0.0" == ip_str):
            return True
        else:
            return False
    
    def intCheck(self,input):
        try:
            int(input)
        except:
            ValueError
            return False
        return True
    
    def stringCheck(self,input):
        if (type(input) == str and len(input) > 0):
            return True
        else:
            return False
            
if __name__ == "__main__":
    configp=parse_config()
    print configp
