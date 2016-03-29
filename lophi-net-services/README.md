# LO-PHI Network Services
This repository hosts all of the network services required by our automation framework for physical host instrumentation.
These services include:
 - **A DNS Server** to ensure that our scripts will work regardless of the IP configuration of the network.
  - This can also be used to reply to specific DNS queries from the SUT
  
 - **A TFTP Server** for hosting an instance of [Clonezilla](http://clonezilla.org/) to save a snapshot of the SUT's hard drive and later clone that saved image back onto the HDD.
 - **A DHCP/PXE Server** to assign and track the IPs of our SUTs as well as enable PXE booting into our Clonezilla instance
 - **An Access-Control Server** to handle when machines can PXE boot and when they should boot from the hard disk.
  - This is neccessary to automate to process and works by turing the machine off and adding it's MAC address to the ACL.
  When the machine turns back on it will PXE boot only once.  So, once the disk is cloned, rebooting the maching will then boot from the newly cloned hard disk.
  
# Dependencies
 * [Pybootd](https://github.com/eblot/pybootd)
 * [proxyDHCPd](https://github.com/gmoro/proxyDHCPd)
 * [CloneZilla](http://clonezilla.org/downloads/download.php?branch=stable)



# Install
All contents are installed into */lophi*

## First, download and extract CloneZilla

1. Download [CloneZilla](https://sourceforge.net/projects/clonezilla/files/clonezilla_live_stable/2.4.5-23/clonezilla-live-2.4.5-23-amd64.zip/download)

2. Extract filesystem.sqaushfs, intrd.img and vmlinuz to *tftpboot/clonezilla-live*.

## Debian (Suggested)
> debuild -uc -us

> sudo dpkg -i [package name].deb 

## Python
> sudo python setup.py install

# Contents
 - **conf** contains a configuration file for out network services
  - *network.conf* must be configured to the proper ip address and have the proper locations for the TFTP server
 - **tftpboot** contains all of the files that will be served by TFTP (e.g. Clonezilla)
 - **net_services_setup.sh** will setup appropriate firewall rules to ensure that lophi-net-services doesn't respond to DHCP requests on eth0 (which could be bad if it is on a shared LAN)

# Disclaimer
<p align="center">
This work was sponsored by the Department of the Air Force under Air
Force Contract #FA8721-05-C-0002.  Opinions, interpretations,
conclusions and recommendations are those of the authors and are not
necessarily endorsed by the United States Government.
<br>
© 2015 Massachusetts Institute of Technology 
</p>
