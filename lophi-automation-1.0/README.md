# LO-PHI Automation Framework
This contains the automation framework used to automate repetitive analysis (e.g., malware analysis).

The general framework is as follows:
 A **master** handles all of the submissions and distribution of analyses.  
 This master connects to numerous **controllers** that are intiialized with pools of either virtual or physical machines.
 The client can use *lophi-submit* to submit executable files that will be uploaded to the *lophi-ftp* server, 
 and stored in a MongoDB database.
 The selected analysis script is then sent from the **master** to the **controller**, 
 which then adds the analysis to a queue that will be assigned the appropriate type of machine when one becomes available.

# Contents
- **actuation_scripts** contains scripts to send keypresses to the SUT to download the binary from our FTP server.
- **analysis_scripts** contains the scripts that perform the actual analysis on the specified machine. 
- **conf** contains numerous configuration scripts
 - *controllers.conf* configures the addresses of the controllers for the master to connect to
 - *images_map.conf* maps operation systems to disk images (e.g., WinXPSP3 -> winxp.img)
 - *sensors.conf* contains all of the information about our physical sensors (e.g., IP address and port)
 - *machines.conf* contains all of the specifications for a physical machine (e.g., sensors, MAC address, RAM size)
- **protocol_buffers** contains numerous descriptions of protocol buffers that are used to communicate and share analysis data.


# Framework Overview
![Overview](../media/overview.png?raw=true)

# Install
All contents are installed into the root directory */lophi/*.  Some of the packages have some subtle post-installation configuration options that should be handled the debian packages *postrm* script, however installing them manually (e.g. python setup.py...) may lead to some confusing bugs down the road.

## Debian (Suggested)
```bash
 $ debuild -uc -us
 $ sudo dpkg -i [package name].deb 
```

## Python
```bash
 $ sudo python setup.py install
```

# Configuration
The automation framework has a significant amount of configuration required.  We will try to outline that below

## Master
The master has a pretty simple configuation that outlines which controllers it shoudl connect to.
These can be found in **/lophi/conf/controllers.conf** and the parameters are as follows:
```config
[<Controller #1 Name>]
host=<IP address or hostname of controller>
port=<Port that the controller is listeneing on>
[<Controller #2 Name>]
...
```
*Note: This can have as many controllers as you'd like.*

## Controller
The controller handles significantly more data and thus has a lot more configuration options
The following configurations files are used to configure physical machine parameters:
* **sensors.conf** - This file contains the information for all of the physical sensors that are available to this controller.  Each sensor is specified in the following way:
```config
[<Name of Sensor (e.g. MemorySensorPCIe)>]
type = <0 - Memory | 1 - Disk | 2 - Control | 3 - CPU | 4 - Nework Tap>
ip = <IP address of sensor (e.g. 172.20.1.10)>
port = <UDP port of sensor (e.g. 31337)>
interface = <physical interface for network tap> (Only relevant for network taps)
...
```
* **machines.conf** - This file specifies characterisitcs about the available physical machines so that our analysis can properly manage them.  Each physical machine must have the following defined:
```config
[<Name of Machine>]
# Memory Sensor
memory_sensor = <Name of memory sensor (as defined in sensors.conf)>
# 1GB
ram_size = <Physical memory size in bytes (e.g. 1073741824 to denote 1 GB)>
# Disk Sensor
disk_sensor = <Name of disk sensor (as defined in sensors.conf)>
# Control Sensor
control_sensor = <Name of control sensor (as defined in sensors.conf)>
# Network Sensor
network_sensor = <Name of network tap (as defined in sensors.conf)>
# Mac Address
mac_address = <MAC address of the NIC that will be interacting with the controller (e.g. for downloading binaries and scripts)>
```

For both physical and virtual machines, we define which disk image should be associated with specific operating system profiles.  We use the exact naming scheme as Volatility for consistency. (e.g. Win7SP0x64)
* **images_map.conf** - This configuration defines the mapping from OS profile to physicla disk image, so that LO-PHI can bootstrap the SUT with the appropriate disk image for the requested analysis.  The mapping is relatively straight forward.
```config
[physical]
<Volatility profile name (e.g. WinXPSP3x86> = <Directory name created by Clonezilla when the 'clean' image was saved.>
...

[virtual]
<Volatility profile name (e.g. WinXPSP3x86> = <Filename of the .img (raw disk image) that was copied from a shutdown KVM instance>
...
```
*Note: the paths are relative in this configuration.  It is assumed that the Clonezilla directories will be in '/lophi/samba/images' and that virtual machine images will be in '/lophi/disk_images/'.*

# Creating 'clean' disk images
The automation framework is designed to have a pool of machines whose operating systems can be dynamically configured.  This enables our disk analysis to always start from the same state, simplifying disk reconstruction tasks, and also enables the same machines to be used for different experiments that require differing operating systems.
Thus, the first step is to generate the clean disk images that the framework will be using.
*Note: We unfortunately only support one image for each operating system profile, for now.*

## Cloning a physical machine's disk
For this task, we use CloneZilla.  The easiest method for doing this is to utilize **lophi-net-services**
1. Get a physical machine's disk in the state that you would like. (e.g. Install desired applications, hibernate, clean shutdown)
2. Ensure that network PXE boot is enabled, and the first option in the SUT's BIOS
3. Start *lophi-net-services*
```bash
 $ sudo /lophi/bin/lophi-net-services
```
4. Manually add the MAC address of the SUT to the access control list.
```bash
 $ ./lophi/bin/lophi-net-pxe -a <MAC address of SUT>
```
5. Turn on the SUT.  At this point it should boot in CloneZilla, and you can follow the onscreen instructions.  Sambda etc. should have already been installed and configured for you by the debian packages.


## Cloning a virtual machine's disk
This setup is significantly easier.
1. Create a virtual machine (virt-manager greatly simplifies this task)
2. Get the virtual machines disk in the state that you would like. 
3. Copy the disk image to */lophi/disk_images/*
```bash
 $ sudo cp /var/lib/libvirt/images/<disk image> /lophi/disk_images/
```
*Note: You may have to chmod these images to ensure that LO-PHI can read them to create copy-on-write disks from them.*

# Running

## Master
For the **master**, the only required process is *lophi-master*, and *lophi-ftp* if you plan to submit binaries.

* A RabbitMQ-based 'master' that corrdinates that handles the various analysis scripts, which are then delegated to 'controllers' that will assign them to machines and executed.
```bash
 $ sudo /lophi/bin/lophi-master
```

## Controller
Each **controller** needs the following:

* An FTP Server for binary submission, and to provide scripts to the SUT
```bash
 $ sudo /lophi/bin/lophi-ftp
```

* a PXE/TFTP/DHCP for physical machine disk reversion *(Note: This is only required if you are dealing with physical machines.)*
```bash
 $ sudo /lophi/bin/lophi-net-services (Requires lophi-net-services package)
```

* Each 'controller' must have a controller instance running. This is what the master will connect to, and what handles of all of the submitted analyses and the pool of machines (both physical and virtual).
```bash
 $ sudo /lophi/bin/lophi-controller
```
*Note: this will only instantiate the basic connfiguration the controller has numerous options:*
```bash
 $ sudo /lophi/bin/lophi-controller --help
```
Some useful configuration options are:
 * **-S** to set the host for the master and mongoDB server 
 * **-t** will create a RAMdisk that it will use for virtual machines, greatly increasing performance
 * **-c** specifies the size of the worker poll of VMs to allocate
 * **--ftp_phy** specifies the physical interface that the SUT's will be connecting to for downloading scripts, binaries, etc.

## Client
At this point, the system is ready to submit binaries:
```bash
 $ /lophi/bin/client/lophi-submit -s [Executable] -p [OS Profile] -T [Machine Type] -a [Analysis Name]
```
For example, to start a GUI-based demo on a virtual machine:
```bash
 $ /lophi/bin/client/lophi-submit -s ~/projects/lophi_software/demo_code/windows/pdf_rootkit/document-hidden.exe -p Win7SP0x64 -T 2 -a gui_demo
```

It is also possible to interact with the system from a command-line-like interface, however this functionality has no gaurantees, as it has been neglected recently.  Typing 'help' will help you navigate the interface though.
```bash
 $ /lophi/bin/client/lophi-client 
.--------------------------------------------.
|                                            |
|          LO-PHI Master Controller          |
|                                            |
+--------------------------------------------+
| -                                        - |
|            Remote Servers: 1               |
|           Remote Machines: 0               |
|                  Analyses: 7               |
| -                                        - |
| -                                        - |
|     Type 'help' for a list of commands.    |
| -                                        - |
`--------------------------------------------'
```

### Data Consummers
We have also developed a few data *consummers* that can consume data from RabbitMQ and manipulate it.
* **lophi-gui** - Will display one window per SUT with continously updated output from our post-semantic-gap memory and disk analysis.
* **lophi-gui-alert** - Will monitor the output from the sensors and only trigger on changes.
* **lophi-gui-graph** - Will attempt to graph statistics about proccess running the machine (probably broken)
* **lophi-logger** - Will simply consume the data from the sensors on RabbitMQ and log them in a nice format.

# Examples
 We included a few examples to demonstrate the basic analysis framework *without* all of the infrastructure.  This could be useful for machines that already running for example, where the automated disk reversion functionality may be overkill.


# Disclaimer
<p align="center">
This work was sponsored by the Department of the Air Force under Air
Force Contract #FA8721-05-C-0002.  Opinions, interpretations,
conclusions and recommendations are those of the authors and are not
necessarily endorsed by the United States Government.
<br>
© 2015 Massachusetts Institute of Technology 
</p>
