"""
    Class for easily interacting with virtual machines

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import multiprocessing
import os
import logging
logger = logging.getLogger(__name__)
from subprocess import call

# LO-PHI
import lophi.globals as G
from lophi.machine import Machine

from lophi.sensors.memory.virtual import MemorySensorVirtual
from lophi.sensors.disk.virtual import DiskSensorVirtual
from lophi.sensors.control.virtual import ControlSensorVirtual
from lophi.sensors.cpu.virtual import CPUSensorVirtual
from lophi.sensors.network.virtual import NetworkSensorVirtual

# Mutex used for libvirt connections
libvirt_mutex = multiprocessing.Lock()


"""
    These are the strings in the template that have to be replaced for a new VM
"""
VIRSH_TEMPLATE = {}
VIRSH_TEMPLATE[G.MACHINE_TYPES.XEN] = """<domain type='xen'>
  <name>%%VMNAME%%</name>
    <uuid></uuid>
  <memory>%%MEM_SIZE%%</memory>
  <currentMemory>%%MEM_SIZE%%</currentMemory>
  <vcpu>%%CPU_COUNT%%</vcpu>
  <os>
    <type>hvm</type>
    <loader>/usr/lib/xen-default/boot/hvmloader</loader>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <pae/>
  </features>
  <clock offset='localtime'>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <devices>
    <emulator>/usr/lib/xen-default/bin/qemu-dm</emulator>
    <disk type='file' device='disk'>
      <driver name='tap' type='qcow2'/>
      <source file='%%DISKIMG%%'/>
      <target dev='xvda' bus='xen'/>
    </disk>
    <interface type='network'>
      <mac address='%%MACADDR%%'/>
      <source network='network-lophi'/>
      <filterref filter='isolated-lophi'>
        <parameter name='GATEWAY_MAC' value='aa:bb:cc:dd:ee:ff'/>
      </filterref>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <input type='tablet' bus='usb'/>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' keymap='en-us'/>
    <sound model='es1370'/>
  </devices>
</domain>
"""
VIRSH_TEMPLATE[G.MACHINE_TYPES.KVM] = """<domain type='kvm'>
  <name>%%VMNAME%%</name>
  <uuid></uuid>
  <memory>%%MEM_SIZE%%</memory>
  <currentMemory>%%MEM_SIZE%%</currentMemory>
  <vcpu>%%CPU_COUNT%%</vcpu>
  <os>
    <type arch='x86_64' machine='pc-i440fx-trusty'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <pae/>
  </features>
  <clock offset='localtime'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <devices>
    <emulator>/usr/bin/kvm-spice</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='%%DISKIMG%%'/>
      <target dev='hda' bus='ide'/>
      <address type='drive' controller='0' bus='0' unit='0'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <target dev='hdc' bus='ide'/>
      <readonly/>
      <address type='drive' controller='0' bus='1' unit='0'/>
    </disk>
    <controller type='ide' index='0'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x1'/>
    </controller>
    <interface type='network'>
      <mac address='%%MACADDR%%'/>
      <source network='network-lophi'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
      <filterref filter='isolated-lophi'>
        <parameter name='GATEWAY_MAC' value='aa:bb:cc:dd:ee:ff'/>
      </filterref>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <input type='tablet' bus='usb'/>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes'/>
    <sound model='ich6'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
    </sound>
    <video>
      <model type='vga' vram='9216' heads='1'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
    </video>
    <memballoon model='virtio'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>
    </memballoon>
  </devices>
</domain>
"""


class REPLACE_STRINGS:
    vm_name = '%%VMNAME%%'
    disk_img = '%%DISKIMG%%'
    mac_addr = '%%MACADDR%%'
    usb_img = '%%USBIMAGE%%'
    memory_size = '%%MEM_SIZE%%'
    cpu_count = '%%CPU_COUNT%%'

    
def generate_new_xen_xml(VIRSH_TEMPLATE, vm_name, 
                         disk_img, 
                         mac_addr, 
                         memory_size=1048576, # 1GB of memory
                         cpu_count=1):
    """
        Given a name, disk, and mac, this will output the appropriate xml 
        config
    """
    tmp = VIRSH_TEMPLATE
    tmp = tmp.replace(REPLACE_STRINGS.vm_name, vm_name)
    tmp = tmp.replace(REPLACE_STRINGS.disk_img, disk_img)
    tmp = tmp.replace(REPLACE_STRINGS.mac_addr, mac_addr)
    tmp = tmp.replace(REPLACE_STRINGS.memory_size, str(memory_size))
    tmp = tmp.replace(REPLACE_STRINGS.cpu_count, str(cpu_count))
    return tmp

        


class VirtualMachine(Machine):


    SNAPSHOT_NAME = "lophisnapshot"

    SNAPSHOT_XML = "\n<domainsnapshot>\n" \
                    "\t<name>%s</name>\n" \
                    "\t<description>LOPHI Snapshot</description>\n" \
                    "</domainsnapshot>\n" % (SNAPSHOT_NAME)

    #/home/lophi/projects/lophi_software/usb.img'/
    USB_XML = "<disk type='file' device='disk'>" \
                " <driver name='qemu' type='raw'/>" \
                " <source file='%%USBIMAGE%%'/> " \
                " <target dev='sda' bus = 'usb'/> " \
                " <alias name='usb-disk0'/> " \
                "</disk>"

    MAC_ADDR = 18090670686208
        
        
    def __init__(self, vm_name, 
                 vm_type=G.MACHINE_TYPES.KVM, 
                 static_mac=None,
                 memory_size=1073741824,
                 cpu_count=1, 
                 force_new=False,
                 volatility_profile=None,
                 **kargs):
        """
            Initialize 
            
            @param config: Machine configuration object
            @param init_sensors: Initialize all sensors by default
        """
        # Initialize our state variables
        self.type = vm_type
        self.MACHINE_TYPE = vm_type
        
        class MachineConfig():
            # Name
            name = vm_name
            # DISK
            disk = os.path.join(G.DIR_ROOT,G.DIR_VM_OUTPUT,vm_name+".qcow2")
            disk_base = None
            # Config
            vm_config = os.path.join(G.DIR_ROOT,G.DIR_VM_OUTPUT,vm_name+".xml")
            
        config = MachineConfig()
        # MAC
        if static_mac is None:
            config.__dict__['mac_addr'] = self.__get_new_mac()
        else:
            config.__dict__['mac_addr'] = static_mac
        config.__dict__['vm_name'] = vm_name
        config.__dict__['memory_size'] = memory_size
        config.__dict__['cpu_count'] = cpu_count
        config.__dict__['volatility_profile'] = volatility_profile
        

        Machine.__init__(self, config)
        
        # Add all of our sensors
        
        # Control sensor must be added first to interact with libvirt
        self.add_sensor(ControlSensorVirtual(vm_name,vm_type))
        
        # What state are we in?
        state = self.control.get_state()
        
        # UKNOWN is does not exist
        if force_new and state is None:
            self.lophi_init()
        elif state != G.SENSOR_CONTROL.POWER_STATUS.UNKNOWN:
            logger.debug("VM (%s) already exists."%self.config.name)
        
        # Add all of our sensors to this VM
        vm_disk = self.disk_get_filename()
        if vm_disk is not None:
            self.add_sensor(DiskSensorVirtual(vm_disk))
        else:
            self.add_sensor(DiskSensorVirtual(self.config.disk))
        self.add_sensor(CPUSensorVirtual(config.vm_name))
        self.add_sensor(MemorySensorVirtual(config.vm_name))
        
        net_iface = self.network_get_interface()
        if net_iface is not None:
            self.add_sensor(NetworkSensorVirtual(net_iface))
        else:
            logger.warn("No network intface exists for %s"%self.config.vm_name)
            
            
        # Do we need to mutex these accesses?
        self.REQUIRE_MUTEX = False
        if "require_mutex" in kargs and kargs['require_mutex']:
            self.REQUIRE_MUTEX = True

        # Force a completely fresh instance?
        if "force_new" in kargs and kargs['force_new']:
            # Poweroff existing machine
            self.control.power_off()
           
           
    def __get_new_mac(self):
    
        # Convert to hex
        mac = hex(VirtualMachine.MAC_ADDR)[2:]
        
        # Increment
        VirtualMachine.MAC_ADDR += 1
        
        # Break into hex sections
        out = []
        for x in range(6):
            out.append(mac[x*2:x*2+2]) 
        
        # return properly formatted MAC
        rtn = ":".join(out)
        logger.debug("Generated MAC: %s"%rtn)
        
        return rtn
        
    def lophi_init(self, force_new=False):
        """
            This will get our machine ready to be used with LO-PHI
        """
        # Check for sensor
        if self.control is None:
            logger.error("No control sensor has been defined for "%self.config.name)
            return
            
        # Create our VM config
        logger.debug("Creating a VM config file for %s..." % self.config.name)
        self.config_create()

#         # Create our disk image    
#         logger.debug("Cloning %s to qcow disk..." % self.machine.config.disk_orig)
#         self.machine.disk_create_cow()
# 
#         # Create our VM instance
#         logger.debug("Creating our VM instance...")
#         self.machine.machine_create()
#         self.machine.machine_resume()


    def set_volatility_profile(self, profile_name):
        """
            Set the profile of this machine.  
            
            In a physical system this will change the pxe image that it restores
            from, if one exists.
            
            In a virtual system, this will change which base disk image we use.
            
            @param profile_name: Profile name of system, based on Volatility's
                                    naming scheme.
        """
        logger.debug("Setting volatility profile for %s to %s...",self.config.name,
                     profile_name)
        self.config.__dict__['volatility_profile'] = profile_name
        
        # Check for sensor
        if not self._has_sensor("control"):
            logger.error("No control sensor has been defined for "%self.config.name)
            return False
        
        if self.images_map is None:
            logger.error("No image map found for %s. (%s)"%(self.config.name,
                                                            profile_name))
            return False
        
        # do we have this profile?
        if profile_name.lower() in self.images_map:
            # Update our disk
            base_filename = self.images_map[profile_name.lower()]
            base_path = os.path.join(G.DIR_ROOT, G.DIR_DISK_IMAGES, base_filename)
            self.config.__dict__['disk_base'] = base_path
            
            logger.debug("Updated base filename for %s to %s."%(self.config.name,
                         self.config.disk_base))
            return True
        else:
            logger.error("No virtual disk image exists for this profile (%s)"%profile_name)
            return False

        
        
    def has_lophi_snapshot(self):
        """
            Check to see if a LO-PHI snapshot exists, if so, we consider
            this machine ready to go.
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        return self.control.has_lophi_snapshot()
    
    
    """
                Actuation Functions
    """
    
    # Defined in Machine
    
    """
                Memory Functions
    """
    # Read and write defined in Machine
        
    def memory_get_size(self):
        """
            Retrieve the allocated memory for this SUT.
            
            @return: Memory size of the SUT it bytes.
        """
        # Check for sensor
        if not self._has_sensor("memory"):
            return
        
        return self.control.memory_get_size()
       
        
    """
                Power functions
                
    """
    # Defined in Machine
    def power_on(self):
        """
            Power on the machine
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        if not self.control.power_on():
            self.machine_create()
            
        # Update state variable
        self.MACHINE_STATE = G.MACHINE_STATES['STARTED']
        

    """
                Machine Control Functions
    """
    
    def machine_create(self, paused=False):
        """
            Creates a new VM from the specified config file.
        """
        if not self._has_sensor("control"):
            return
        
        
        # Read our XML config and create a new machine
        xml_config = self.config_read()
        
        rtn = self.control.machine_create(xml_config,paused)
        
        # Now that the machine is created our network should be setup
        net_iface = self.network_get_interface()
        if net_iface is not None:
            self.add_sensor(NetworkSensorVirtual(net_iface))
        else:
            logger.warn("No network intface exists for %s"%self.config.vm_name)
            
        return rtn



    def machine_pause(self):
        """
            Pause a machine
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        self.control.machine_pause()

        self.MACHINE_STATE = G.MACHINE_STATES['PAUSED']


    def machine_resume(self):
        """
            Resume a paused machine
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return

        self.MACHINE_STATE = G.MACHINE_STATES['RESUMING']

        self.control.machine_resume()

        self.MACHINE_STATE = G.MACHINE_STATES['STARTED']
        self.DISK_STATE = G.DISK_STATES['DIRTY']
        
        
    """
                Snapshot functions
    """
    
    def machine_snapshot(self):
        """
            Takes a snapshot of the VM and freezes it.
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        self.MACHINE_STATE = G.MACHINE_STATES['SNAPSHOTTING']
        
        rtn = self.control.machine_snapshot()
        # Update state variable
        self.MACHINE_STATE = G.MACHINE_STATES['OFF']
        
        return rtn


    def machine_snapshot_restore(self):
        """
                Restore a previously snapshotte version of the machine
        """

        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        return self.control.machine_snapshot_restore()
    
    
    def machine_save(self):
        """
            Suspends machine and saves state to a file.
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        self.MACHINE_STATE = G.MACHINE_STATES['SNAPSHOTTING']

        self.control.machine_save(self.config.disk_snapshot)

        self.MACHINE_STATE = G.MACHINE_STATES['OFF']


    def machine_restore(self, paused=False):
        """
            Restore a machine from our saved state and start it
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        self.control.machine_restore(self.config.disk_snapshot, paused)

        self.MACHINE_STATE = G.MACHINE_STATES['STARTED']
        self.DISK_STATE = G.DISK_STATES['DIRTY']
        
    
        
    """
                Disk management functions
                @TODO: Store our configuration variables in libvirt so that
                        our control sensor can access them
    """
    
    def disk_revert(self):
        """
            Overwrite the disk with a backup of our original
        """

        logger.debug("Reverting disk of %s..." % self.config.name)

        if self.config.disk_base is not None:
            self.disk_create_cow(self.config.disk_base)
            return True
        else:
            logger.error("No base disk image found for %s."%self.config.name)
            return False

    
    def disk_backup(self):
        """
            Create a backup of the disk to revert to later
        """
        call(["cp", self.config.disk, self.config.disk_orig])


    """    Virtual Machine Only    """
    
    def disk_create_cow(self, base_filename):
        """
            Will generate a qcow disk for this VM
        """
        
        logger.debug("Creating qcow disk from %s for %s..."%(base_filename,
                                                             self.config.name))
        
        self.config.__dict__['disk_base'] = base_filename
        
        call(["qemu-img", "create", "-b%s" % base_filename, "-fqcow2", self.config.disk])
        
        
    def disk_get_filename(self):
        """
            Retrieve the filename of the disk used by this SUT.
            
            @return: Filename of backing disk.
        """
        # Check for sensor
        if not self._has_sensor("control"):
            return
        
        filename = self.control.disk_get_filename()

        return filename
    
    """
            VM Config functions
    """

    def config_create(self):
        """
            Create our config file on disk to be loaded into Xen
        """
        logger.debug("Creating new machine. (%s)"%self.config.mac_addr)
        
        config = generate_new_xen_xml(VIRSH_TEMPLATE[self.type],
                                      self.config.vm_name,
                                         self.config.disk,
                                         self.config.mac_addr)
        f = open(self.config.vm_config, "w+")
        f.write(config)
        f.close()

    def config_read(self):
        """
            Read our xml config content
        """

        if not os.path.exists(self.config.vm_config):
            self.config_create()

        f = open(self.config.vm_config, "r")
        config_content = f.read()
        f.close()

        return config_content
    
    
    """
        Network Functions
    """
    
    def network_get_ip(self):
        """
            Return the IP of the virtual machine using only the MAC address
            
            @return: IP address if it can be determined or None
        """
        lease_file = "/var/lib/libvirt/dnsmasq/default.leases"
        
        if os.path.exists(lease_file):
            logger.debug("Found lease file, looking for NAT'ed leases.")
            f = open(lease_file,"r")
            for line in f:
                columns = line.split()
                mac_addr = columns[1]
                ip_addr = columns[2]
                
                if mac_addr == self.config.mac_addr:
                    return ip_addr
                
            logger.debug("Nothing in lease file, Trying arp...")
            import subprocess
            import sys
            cmd="arp -an"
            p=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            output, errors = p.communicate()
            
            if output is not None :
                if sys.platform in ['linux','linux2']:
                    for line in output.split("\n"):
                        columns = line.split()
                        if len(columns) > 3 and self.config.mac_addr in columns[3]:
                            return columns[1][1:-1]
                            
#                 elif sys.platform in ['win32']:
#                     item =  output.split("\n")[-2]
#                     if remotehost in item:
#                         print "%s-->  %s" %(remotehost, item.split()[1])
        else:
            logger.debug("No lease file found.")
            
        # Try the default which is our dhcp server
        
        return None
    
    def network_get_interface(self):
        """
            Dump the xml configuration and get the network interface assigned 
            to this virtual machine.
            
            @return: Interface name or None
        """
        return self.control.network_get_interface()
        
    
    """
        Miscellanous Funcitons
    """
    def screenshot(self,filename,vol_uri=None):
        """
            Screenshot the display of the machine and save it to a file.
            
            @param filename: Filename to save screenshot data to.
            @param vol_uri: UNIMPLEMENTED Just here to be compatible with Physical 
        """
        return self.control.screenshot(filename)
    


class VirtualMachineCreator(multiprocessing.Process):
    """
        This class is meant to aide generating snapshots of VM's by launching
        a separate process to snapshot numerous VM's in parallel
    """
    def __init__(self, machine, **kargs):
        """
            Initialize all of our VM params for future reference
        """
        self.machine = machine

        # Init our multiprocess
        multiprocessing.Process.__init__(self)

    
    def set_sleep_time(self, sleep_time):
        """ 
            Set the number of seconds that we should sleep before we take a 
            snapshot
        """
        self.sleep_time = sleep_time



    def run(self):
        """
            Run the appropriate commands to start the VM and snapshot it.
        """

        # Create our VM config
        print "* Creating a VM config file for %s..." % self.machine.config.name
        self.machine.config_create()

        # Create our disk image    
        print "* Cloning %s to qcow disk..." % self.machine.config.disk_orig
        self.machine.disk_create_cow()

        # Create our VM instance
        print "* Creating our VM instance..."
        self.machine.machine_create()
        self.machine.machine_resume()

        # Sleep for the allotted time
        from time import sleep
        print "* Sleeping for %d seconds. See you in a few..." % (self.sleep_time)
        sleep(self.sleep_time)

        # Create our disk image
        print "* Snapshotting %s..." % (self.machine.config.vm_name)
#        self.machine_pause()
        self.machine.machine_save()

        # Store a copy in our orig directory for reverting
        print "* Backing up disk..."
        self.machine.disk_backup()

        # Scan our disk image
        print "* Converting disk back to raw to scan..."
        self.scan_raw_img()

        print "* Done."
