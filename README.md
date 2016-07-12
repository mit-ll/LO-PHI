![Logo](media/LO-PHI_black_transparent.png?raw=true)


                       Low-Observable Physical Host Instrumentation

# Overview
LO-PHI is a distributed hardware and software platform that aims to instrument both physical and virtual machines through the use of novel sensors and accompanying data analysis tools.  The current suite of capabilities includes: memory introspection, disk activity monitoring, keyboard and mouse actuation, and power management.  Future versions will also include CPU introspection.  For virtual hosts, these capabilities are provided in a popular open-source hypervisor, QEMU-KVM, by custom hooks inserted into the source code.  Similarly, for physical hosts, there is custom hardware to provide the same sensor capabilities.  For asynchronous memory introspection we have both a PCI and PCI-Express card which are both capable of direct memory access (DMA), and for disk access monitoring we developed a Serial ATA (SATA) interposer which enables us to monitor any SATA-capable disk drives.  These are implemented on various  development field-programmable gate arrays (FPGAs).  Finally, all of the sensors have accompanying application programming interfaces (APIs), written in Python, to facilitate end-user interaction as well as a suite of deployment and analytics tools for rapid deployment and prototyping using our sensors.  The analytics tools are built on popular and powerful open-source forensics tools, i.e. Volatility and Sleuthkit, which enable a wide range of capabilities right out of the box, e.g. enumerate running processes and file system operations for popular operating systems.  Because of the numerous foreseeable applications of LO-PHI technologies, we developed the architecture in a modular way such that any set of our sensors and analytics tools can be used in isolation or in unison, thus providing the end-user with the flexibility to fit a solution their problem without any unnecessary hurdles.

# Contents

## Scripts
 - **setup_dev_environment.sh** is a script to update PYTHONPATH appropriately for development also create symbolic links
  > source setup_dev_environment.sh
 - **distribute_deb.sh** is a script to distribute the debian packages to a apt repostitory
 - **build_deb.sh** will build all of the debian packages and place them in *dist*

## Python modules
 - **python-lophi-1.0** is the main python module for actually instrumenting machines
 - **python-lophi-process-under-test-1.0** is a ***beta*** module for working with processes under test.
 - **python-lophi-semanticgap-1.0** is a python module for bridging the semantic gap from the raw data obtained by python-lophi to human readable forms (e.g., process lists, file system activity)

## Packages
 - **lophi-automation-1.0** is a framework for automated analysis with instrumented machines
 - **lophi-net-services-1.0** contains numerous network services that faciitate lophi-automation
 - **lophi-analysis-1.0** contains numerous analysis scripts used to analyze the data collected by lophi-automation

## Miscellaneous
 - **experiments** contains numerous experiments and scripts for plotting the resulting data to test numerous aspects of LO-PHI
 - **demo_code** contains source code and compiled binaries for programs that are used for demonstrating LO-PHI's capabilities
 - **dist** contains distributable binaries for the included packages
 - **tools** contains numerous useful tools for working with various aspects of LO-PHI (e.g. manipulating disk images, pinging the sensors)
 - **deployments** contains code for any deployments of LO-PHI that have been specially developed and deployed
 - **sut_software** contains binaries that are useful to have on a system under test
 - **docs** useful documentation

# Installation
We briefly outline the steps for installing LO-PHI and it's dependencies below.

## Developers

For those wishing to modify or further develop LO-PHI, we do not recommend
installing the packages, but instead provide a script to setup your
environmental variables for easy in-place development:

 > ./setup_dev_environment.sh

 > source setup_dev_environment.sh

## Users
All of the packages can be installed by either installing the Debian package
  > dpk -i [package name].deb

  if you have an apt repository configured:

  > sudo apt-get install [package name]

  or by using the typical Python install

  > sudo python setup.py install

  We recommend using the debian package as this will place everything under the
  **/lophi** root directory and hand some important post-install routines.

## Dependencies

LO-PHI has numerous packages associated with it, currently located in a separate
repository (lophi-packages), which include QEMU-KVM, Volatility, Sleuthkit,
PyTSK, and a disk introspection server.  The easiest way to install these is by
using the script provided in the repository.  (Again, installing using the
Debian package is preferred due to important post-install procedures)

  > ./install_lophi_packages.sh

Once the packages are installed you can interact with the Virtual and Physical
machines using the scripts provided in *python-lophi-1.0/examples/*.

### Virtual Machines

As a quick sanity test, we recommend starting a VM and trying the following
commands:

  * **lophi_disk_introspection_status** - Will list the virtual disks that are
  available for introspection.
  * **./example_memory.py -T 2 -t [vm name]** - Will dump a small section of
  memory from the VM
  * **./capture_disk.py -T 2 -t [vm name]** - Will start capturing disk activity
  from the VM.
  * **./example_control.py -T 2 -t [vm name] -s hello_world_windows.act** - Will
  actuate the keyboard and open a command prompt.
  * **./example_control.py -T 2 -t [vm name] -m 100,100** - Will Actuate the mouse
  and click the top-left corner of the screen.

  Confirm that their is output from all of these.


### Physical Machines

Similarly, the same scripts apply with different type (-T) and target (-t)
parameters.  The default IPs that we assigned our sensors are:

* **Memory Sensor (PCIe)**: 172.20.1.11
* **Memory Sensor (PCI)**: 172.20.1.3
* **LO-PHI Disk Sensor**: 172.20.1.1
* **LO-PHI Control Sensor**: 172.20.1.20

and the network card interacting with the sensors should have the IP: **172.20.1.2**


## Automation Framework and Semantic-Gap Reconstruction
Please see the respective projects README files for more in-depth explanation
of their installation and usage.

# Debugging

## Disk introspection

 * First, make sure that the disk introspection server is running:
 ```bash
$ lophi-disk-introspection-status 

Status of connected guest VMs...

 ID : Status : HDD Filename
 --   ------   ----------------------------------------
069 :   open : /var/lib/libvirt/images/example.img

Status of waiting clients...

 SOCK :  HDD Filename
 ----   ----------------------------------------
```

 * If you don't see a disk listening, ensure that you are running the properly patched version of QEMU:
 ```bash
 $ tail -f /var/log/syslog | grep -i lophi
 ```
  - If you dont see any output, follow the install steps to re-install our patched qemu-kvm instance.
  - If you see permission denied errors, try running the *scripts/fix_kvm_install.sh* script, as this is likely a problem with **apparmor**.

 * To test the server, you can netcat into the disk introspection server (type *h* for help):
 ```bash
$ nc localhost 31337
h
LO-PHI Disk Introspection Server
Commands
   l - list running VM's
   i <vm id> - subscribe to VM with specified ID
   n <vm filename> - subscribe to VM with specified filename
```


## Memory Introspection

 * If you are getting strange errors with Volatility/libvmi like:

    error: no connection driver available for No connection for URI xen:///
    error: failed to connect to the hypervisor

 It's likely because your VIRSH_DEFAULT_CONNECT_URI environment variable is set
 incorrectly.  Unset this a try again.


 * Remember that libvmi must be run as root!

    PyVmiAddressSpace - EXCEPTION: Init failed

    is a likely error if you're not root.


## KVM


  * We had to set cache='none' in the virsh config to improve speed for snapshots

  * You may have to edit /etc/libvirt/qemu.conf to enable it run as root.  Look for 2 commented lines ?root

  * Some tips for managing VMs:
   http://serverfault.com/questions/373372/how-to-connect-a-cdrom-device-to-a-kvm-qemu-domain-using-command-line-tools


## Setup PXE Boot Server

 * IMPORTANT: There is a bug in the version of Clonezilla we are using.
              You MUST make sure that your MTU is 1500, jumbo frames will break

 * http://www.debian-administration.org/articles/478


# References

  * Install python as a service: http://stackoverflow.com/questions/4705564/python-script-as-linux-service-daemon

# Acknowledgments

## Open Source Software:
 Volatility, Sleuthkit, pybootd, pyproxydhcp, Clonezilla, analyzeMFT

## Hardware:
 Xilinx, Arduino

## People:
 Josh Hodosh, Ryan Whelan, Charles Wright, Jenny Mankin, Antonio Godfrey, Brendon Chetwynd, Kevin Leach

# Disclaimer
<p align="center">
This work was sponsored by the Assistance Secretary of Defense for Research and
Engineering under Air
Force Contract #FA8721-05-C-0002.  Opinions, interpretations,
conclusions and recommendations are those of the authors and are not
necessarily endorsed by the United States Government.
<br>
© 2015-2016 Massachusetts Institute of Technology
</p>
