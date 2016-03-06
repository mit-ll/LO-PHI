"""
    Class for controlling virtual machines using libvirt

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import multiprocessing
import logging
logger = logging.getLogger(__name__)
import time
import os
import shutil

from subprocess import call

# 3rd Party
try:
    import libvirt
except:
    logger.error("python-libvirt is not installed! (sudo apt-get install python-libvirt)")

# LO-PHI
import lophi.globals as G
from lophi.sensors.control import ControlSensor
from lophi.actuation.keypressgenerator import KeypressGeneratorVirtual
import lophi.actuation.rfb as RFB

# Mutex used for libvirt connections
libvirt_mutex = multiprocessing.Lock()


XML_NETWORK = """
<network>
  <name>network-lophi</name>
  <bridge name='lophi-virt' stp='off' delay='0' />
  <mac address='aa:bb:cc:dd:ee:ff'/>
  <ip address='192.168.1.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.1.2' end='192.168.1.254' />
    </dhcp>
  </ip>
</network>
"""

XML_NWFILTER = """
<filter name='isolated-lophi' chain='root'>
  <rule action='drop' direction='in' priority='500'>
    <mac match='no' srcmacaddr='$GATEWAY_MAC'/>
  </rule>
</filter>
"""

class ControlSensorVirtual(ControlSensor):
    """
        Control sensor for Virtual machines
    """
    ISOLATED_NETWORK_CREATED = False
    def __init__(self, vm_name, vm_type=None,isolated_network=True, **kargs):
        """
            Initialize 
        """
        if os.getuid() != 0:
            logger.error("You likely have to run libvirt as root.")
        
        # Do we need to mutex these accesses?
        self.REQUIRE_MUTEX = False
        if "require_mutex" in kargs and kargs['require_mutex']:
            self.REQUIRE_MUTEX = True
        
        # Meta data    
        self.vm_name = vm_name
        self.MACHINE_TYPE = vm_type
        self.name = vm_name+"-ControlSensor"
        
        # Should this be created on the isolated LO-PHI network?
        self.ISOLATED_NETWORK = isolated_network
                
        # See if our VM already exists
        dom = self._connect()
        
        # Dose our domain exist?
        if dom is not None and vm_type is None:
            # Let's determine the type of VM automatically
            logger.debug("Detecting type of vm for %s"%self.vm_name)
            
            from xml.dom.minidom import parseString
            xml = dom.XMLDesc(0)
            xml_dom = parseString(xml)
            root_node = xml_dom.childNodes[0]
            
            domain_type = root_node.getAttribute("type")
            
            if domain_type == "kvm":
                self.MACHINE_TYPE = G.MACHINE_TYPES.KVM
            elif domain_type == "xen":
                self.MACHINE_TYPE = G.MACHINE_TYPES.XEN
        
        # If we are creating it from within LO-PHI make sure we use our 
        #  isolated network
        if self.ISOLATED_NETWORK and not self.ISOLATED_NETWORK_CREATED:
            net = nwf = None
            try:
                # Create our filter and our network
                try:
                    net = self._libvirt_conn.networkLookupByName("network-lophi")
                except:
                    pass
                try:
                    nwf = self._libvirt_conn.nwfilterLookupByName("isolated-lophi")
                except:
                    pass
            
                # Create our network and filter if they don't already exist
                if net is None or net is "":
                    self._libvirt_conn.networkCreateXML(XML_NETWORK)
                if nwf is None or nwf is "":
                    self._libvirt_conn.nwfilterDefineXML(XML_NWFILTER)
                
                ControlSensorVirtual.ISOLATED_NETWORK_CREATED = True
                logger.debug("Isolated network and rules created")
            except:
                logger.error("Could not create libvirt isolated network!")
                pass
            
        self._disconnect()
        
        # Ensure we know what type of meachine we are working with
        if self.MACHINE_TYPE is None:
            logger.error("No machine type given for %s, defaulting to KVM"%self.vm_name)
            self.MACHINE_TYPE = G.MACHINE_TYPES.KVM    
            
        
        ControlSensor.__init__(self)


    def _connect(self):
        """
            Create our libvirt connection
        """

        # Get our mutex!
        if self.REQUIRE_MUTEX:
            libvirt_mutex.acquire()

        # Open our libvirt connection
        self._libvirt_conn = libvirt.open(None)  # $LIBVIRT_DEFAULT_URI, or give a URI here
        assert self._libvirt_conn, 'libVirt: Failed to open connection'

        # logger
        logger.debug("* Connecting %s" % self.vm_name)

        # Try to lookup our domain to see if it exists and return it
        try:
            dom_tmp = self._libvirt_conn.lookupByName(self.vm_name)
            return dom_tmp
        except:
            return None
            pass


    def _disconnect(self):
        """
            Disconnect from libvirt
        """
        # Close libvirt
        self._libvirt_conn.close()

        # Release our mutex!
        if self.REQUIRE_MUTEX:
            libvirt_mutex.release()
    
    
    
    
    """
            Actuation functions
    """
    
    
    def _get_vnc_port(self):
        """
            Return the VNC port for this virtual machine through libvirt
        """
        vnc_port = None

        DOM = self._connect()

        if DOM is None:
            logger.error("VM %s was not found." % self.vm_name)
            
        else:
            # Extract the VMs XML config
            xml_str = DOM.XMLDesc(0)
            import xml.dom.minidom as xml

            # Extract all graphics objects
            dom = xml.parseString(xml_str)            
            graphics = dom.getElementsByTagName("graphics")
    
            # Look for one of type="vnc" and extract its port
            for g in graphics:
                g_type = g.getAttribute("type")
                if g_type == "vnc":
                    port = g.getAttribute("port")
                    vnc_port = int(port)

        self._disconnect()
        
        return vnc_port
    
    
    def mouse_click(self,x,y,button=RFB.MOUSE_LEFT,double_click=False):
        """
            This will move the mouse the specified (X,Y) coordinate and click
           
            NOTE: Unfortuantely we have to use the VNC interface.  Libvirt 
            doesn't have an exposed API for mouse functions
            
            @param x: X coordinate on the screen
            @param y: Y coordinate on the screen
            @param button: Button mask for what to click 
                            (0b1 - Left, 0b100 - Right)
            @param double_dlick: Specifies a double click or single click
        """
        
        vnc_host="localhost"
        vnc_port=self._get_vnc_port()

        if vnc_port is None:
            logger.error("Could not detect a VNC port for %s"%self.name)
            return False
        
        # Use our RFB Client
        vnc_client = RFB.RFBClient(vnc_host,vnc_port)
        vnc_client.mouseMove(x ,y)
        vnc_client.mouseClick(button,double_click=double_click)
        
        time.sleep(.5)
        return True
    
    def mouse_wiggle(self, enabled):
        """ This function randomly wiggles the mouse """
        
        # We do not currently implement this for virtual machines
        return True
    
    
    def keypress_send(self, keypresses):
        """
            Given a list of keypress instructions will emulate them on the SUT.
            
            @param keypresses: List of lists of keypresses with SPECIAL/TEXT 
                               identifiers.
                               E.g. [ [Type, [Keys] ], ... ] 
        """
        logger.debug("Sending key press")

        # Start emulating 
        DOM = self._connect()

        if DOM is None:
            logger.error("Could not find VM (%s)" % self.vm_name)
        else:
    
            # Open Run Dialog
            for line in keypresses:
                cmd = line[0]
                keys = line[1]
    
                # Special key?
                if cmd == G.SENSOR_CONTROL.KEY_SP_CMD:
                    DOM.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 0, keys, len(keys), 0)
                
                # Are we sleeping?
                elif cmd == G.SENSOR_CONTROL.KEY_SLEEP:
                    logger.debug("Key press: Sleeping for %d "%int(keys))
                    
                    time.sleep(int(keys))
                    
                # Normal keys                    
                else:
                    for c in keys:
                        if isinstance(c, list):
                            DOM.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 0, c, len(c), 0)
                        else:
                            DOM.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 0, [c], 1, 0)
                        time.sleep(G.SENSOR_CONTROL.SLEEP_INTER_KEY)
    
                time.sleep(G.SENSOR_CONTROL.SLEEP_INTER_CMD)

        self._disconnect()
    
    
    def keypress_get_generator(self):
        """
            Return a generator to convert scripts into a language this sensor 
            understands
            
            @return: KeypressGenerator for virtual machines
        """
        
        return KeypressGeneratorVirtual()
    
    """
                Power functions
    """
            
    def power_on(self):
        """
            Power on the VM
        """
        logger.debug("Starting up %s..." % self.vm_name)

        DOM = self._connect()
        if DOM is not None:
            # Machine is already on if this is set
            try:
                DOM.create()
            except:
                pass
            rtn = True    
        else:
            logger.warning("%s does not exist." % self.vm_name)
            rtn = False
            
        self._disconnect()
        
        return rtn
        
        
    def power_off(self):
        """
            Hard shutdown the machine
        """
        logger.debug("* Destroying %s..." % self.vm_name)

        try:
            DOM = self._connect()
            if DOM is not None:
                DOM.destroy()
            else:
                logger.error("%s does not exist." % self.vm_name)
            self._disconnect()
        except:
            logger.error("* Cannot destroy machine, %s"%self.vm_name)
            
    
    def power_shutdown(self):
        """
            Nice shutdown of the VM
        """
        logger.debug("Shutting down %s..." % self.vm_name)

        DOM = self._connect()
        if DOM is not None:
            DOM.shutdown()
        else:
            logger.error("%s does not exist." % self.vm_name)
        self._disconnect()
            
            
    def power_reset(self):
        """
            Reset power on the VM
        """
        logger.debug("Resetting %s..." % self.vm_name)

        DOM = self._connect()
        if DOM is not None:
            DOM.reset(0)
        else:
            logger.error("%s does not exist." % self.vm_name)
        self._disconnect()
        
        
    def power_reboot(self):
        """
            Reboot the VM
        """
        logger.debug("Rebooting %s..." % self.vm_name)

        DOM = self._connect()
        if DOM is not None:
            DOM.reboot(0)
        else:
            logger.error("%s does not exist." % self.vm_name)
        self._disconnect()

        
    def get_state(self):
        """
            Return the current state of the VM
        """
        DOM = self._connect()
        if DOM is not None:
            rtn = DOM.state(0)
        else:
            rtn = None
        
        self._disconnect()
        
        return rtn
    
        
    def power_status(self):
        """
            Return the status of the VM
        """
        
        logger.debug("Getting power status of %s..." % self.vm_name)

        
        state = self.get_state()
        
        if state is None:
            return G.SENSOR_CONTROL.POWER_STATUS.UNKNOWN
        
        # For some reason a list is returned, seem to always be the same.
        state = state[0]
        
        # Running?
        if state in [libvirt.VIR_DOMAIN_RUNNING,
                     libvirt.VIR_DOMAIN_BLOCKED,
                     libvirt.VIR_DOMAIN_PAUSED
                     ]:
            return G.SENSOR_CONTROL.POWER_STATUS.ON
        
        # Off?
        elif state in [libvirt.VIR_DOMAIN_SHUTDOWN,
                     libvirt.VIR_DOMAIN_SHUTOFF]:
            return G.SENSOR_CONTROL.POWER_STATUS.OFF
        
        # Unknown?
        elif state in [libvirt.VIR_DOMAIN_NOSTATE,
                     libvirt.VIR_DOMAIN_CRASHED,
                     libvirt.VIR_DOMAIN_LAST]:
            return G.SENSOR_CONTROL.POWER_STATUS.UNKNOWN
        else:
            logger.warning("%s does not exist." % self.vm_name)
            return G.SENSOR_CONTROL.POWER_STATUS.UNKNOWN
        
        
        
    """
            Machine control functions
    """
    def machine_create(self, xml_config, paused=False):
        """
            Creates a new Xen VM from the specified config file.
        """
        logger.debug("Creating %s... (Paused=%s)" % (self.vm_name, paused))
        
        DOM = self._connect()
        # Is there a machine already created?
        if DOM is not None:
            logger.error("Tried to created %s, but a VM already exists." % self.vm_name)
        else:
            
            # Create our machine
            if paused:
                if self.MACHINE_TYPE == G.MACHINE_TYPES.KVM:
                    DOM = self._libvirt_conn.createXML(xml_config,
                                                   libvirt.VIR_DOMAIN_START_PAUSED)
                else:
                    DOM = self._libvirt_conn.createXML(xml_config, 0)
                    DOM.suspend()
            else:
                logger.debug("Creating VM unpaused.")
                DOM = self._libvirt_conn.createXML(xml_config, 0)

        self._disconnect()
            
    
    def machine_pause(self):
        """
            Pause a machine
        """
        logger.debug("Pausing %s..." % self.vm_name)

        DOM = self._connect()
        if DOM is not None:
            DOM.suspend()
        else:
            logger.error("%s does not exist." % self.vm_name)
        self._disconnect()

    
    def machine_resume(self):
        """
            Resume a paused machine
        """
        logger.debug("Resuming machine %s..."%self.vm_name)

        DOM = self._connect()
        if DOM is not None:
            DOM.resume()
        else:
            logger.error("%s does not exist." % self.vm_name)
        self._disconnect()
        
    
    """
                Snapshot Functions
    """
    
    def machine_snapshot(self):
        """
            Takes a snapshot of the VM and freezes it.
        """
        logger.debug("Taking snapshot of %s..." % self.vm_name)

        if self.MACHINE_TYPE == G.MACHINE_TYPES.XEN:
            logger.warning("Xen doesn't have snapshot capabilities!")
            return False

       
        # First let's see if our snapshot already exist?
        DOM = self._connect()

        if DOM is not None:
            if self.MACHINE_TYPE == G.MACHINE_TYPES.KVM:
                try:
                    DOM.snapshotLookupByName(self.SNAPSHOT_NAME, 0)
                    logger.warning("Snapshot already exist for %s" % self.vm_name)
                except:
                    DOM.snapshotCreateXML(self.SNAPSHOT_XML, 0)
            else:
                logger.error("%s does not exist." % self.vm_name)

        self._disconnect()
        
    
    def machine_snapshot_restore(self):
        """
                Restore a previously snapshotte version of the machine
        """
        logger.debug("Restoring snapshot of %s..." % self.vm_name)

        if self.MACHINE_TYPE == G.MACHINE_TYPES.XEN:
            logger.warning("Xen doesn't have snapshot capabilities! (Using reset/restore)")
            self.machine_reset()
            self.machine_restore()
            return False

        # Try to detach our USB key
        self.detach_usb()

        # Does our snapshot exist?
        DOM = self._connect()
        rtn = False
        if DOM is not None:
            if self.MACHINE_TYPE == G.MACHINE_TYPES.KVM:
                try:
                    snap = DOM.snapshotLookupByName(self.SNAPSHOT_NAME, 0)
                    DOM.revertToSnapshot(snap, libvirt.VIR_DOMAIN_SNAPSHOT_REVERT_PAUSED)
                    rtn = True
                except:
                    logger.error("Tried to revert %s to snapshot when none exist!" % self.vm_name)
            else:
                logger.error("%s does not exist." % self.vm_name)

        self._disconnect()

        return rtn
    
    
    def machine_save(self, filename):
        """
            Suspends machine and saves state to a file.
        """
        logger.debug("Saving state of %s..." % self.vm_name)

        if self.MACHINE_TYPE == G.MACHINE_TYPES.XEN:
            # In Xen the machine must be "running" to save.
            self.machine_resume()

        DOM = self._connect()
        
        if DOM is not None:
            DOM.save(filename)
        else:
            logger.error("%s does not exist." % self.vm_name)
            
        self._disconnect()
        
        
    def machine_restore(self, filename, paused=False):
        """
            restore a machine from our snapshotted state and start it
        """
        logger.debug("Restoring %s..." % self.vm_name)

        self.MACHINE_STATE = G.MACHINE_STATES['RESTORING']

        self._connect()
        if self.MACHINE_TYPE == G.MACHINE_TYPES.KVM:
            if paused:
                self._libvirt_conn.restoreFlags(filename, None, libvirt.VIR_DOMAIN_SAVE_PAUSED)
            else:
                self._libvirt_conn.restore(filename)
        else:
            if paused:
                logger.error("Unable to restore Xen paused without command line hack...")
            else:
                self._libvirt_conn.restore(filename)

        self._disconnect()
    
    """
        Miscellaneous functions
    """
    def screenshot(self, filename):
        """
            Screenshot the display of the machine and save it to a file.
            
            @param filename: Filename to save screenshot data to. 
        """
        rtn = filename+".ppm"
        
        def saver(stream, data, file_):
            return file_.write(data)
        
        DOM = self._connect()
        
        if DOM is not None:
            try:
                # Create a new virtual stream
                stream = self._libvirt_conn.newStream(0)
                
                # Take our screenshot
                DOM.screenshot(stream, 0, 0)
                
                # save to file
                f = open(rtn, 'w+')
                stream.recvAll(saver, f)
                f.close()
                
                # Finish and return
                stream.finish()
            except:
                rtn = False
        else:
            logger.error("%s does not exist." % self.vm_name)
            
        self._disconnect()
        
        return rtn
        
    
    
    """
        VM Only Functions
    """
    
    def memory_get_size(self):
        """
            Return the memory size in bytes of this virtual machine
            
            @return: Memory size in bytes
        """
        
        rtn = None
        DOM = self._connect()

        if DOM is None:
            logger.error("VM %s was not found." % self.vm_name)
            rtn = None
        else:
                
            xml_str = DOM.XMLDesc(0)
    
            logger.debug("Getting memory size from %s"%xml_str)
            import xml.dom.minidom as xml
    
            dom = xml.parseString(xml_str)
            mem = dom.getElementsByTagName("currentMemory")
    
            for m in mem:
                unit = m.getAttribute("unit")
                if unit == "KiB":
                    rtn = int(m.childNodes[0].data)*1024
                else:
                    logger.error("Found a unit that we don't support when calculating memory size! (%s)"%unit)

        self._disconnect()

        return rtn
    
    def disk_get_filename(self):
        """
            Retrieve the filename of the disk used by this SUT.
            
            @return: Filename of backing disk.
        """
        filename = None

        DOM = self._connect()

        if DOM is None:
            logger.error("VM %s was not found." % self.vm_name)
            
        else:
                
            xml_str = DOM.XMLDesc(0)
    
            logger.debug("Getting disk from %s"%xml_str)
            import xml.dom.minidom as xml
    
            dom = xml.parseString(xml_str)
            disks = dom.getElementsByTagName("disk")
    
            for d in disks:
                device = d.getAttribute("device")
    
                if device == "disk":
                    source = d.getElementsByTagName("source")
                    fname = source[0].getAttribute("file")
                    filename = fname

        self._disconnect()

        return filename
    
    
    """
            Network Functions
    """            
            
    def network_get_interface(self):
        """
            Dump the xml configuration and get the network interface assigned 
            to this virtual machine.
            
            @return: Interface name or None
        """
        iface_dev = None

        DOM = self._connect()

        if DOM is None:
            logger.error("VM %s was not found." % self.vm_name)        
        else:
    
            try:
                xml_str = DOM.XMLDesc(0)
        
                import xml.dom.minidom as xml
        
                dom = xml.parseString(xml_str)
                iface = dom.getElementsByTagName("interface")
        
                target = iface[0].getElementsByTagName("target")
                iface_dev = target[0].getAttribute("dev")
            except:
                logger.error("Could not find network interface for %s"%self.vm_name)

        self._disconnect()

        return iface_dev
    
    
    def has_lophi_snapshot(self):
        """
            Check to see if a LO-PHI snapshot exists, if so, we consider
            this machine ready to go.
        """
        rtn = False

        DOM = self._connect()

        if DOM is not None:
            try:
                DOM.snapshotLookupByName(self.SNAPSHOT_NAME, 0)
                rtn = True
            except:
                pass
        else:
                pass

        self._disconnect()

        return rtn
    
    
    """
        Experimental Functions
    """
    
#     # TODO: This is too much for this class to be doing!
#     def run_code(self, input_directory, ftp_info):
#         """
#             Will download the entire directory to the SUT and run lophi.bat
#             
#             @param input_directory: Directory with executable code and lophi.bat
#             
#         """
#         import time
#         import lophi.actuation.scripts as S
# 
#         if not os.path.exists(input_directory):
#             print "ERROR: input directory (%s) does not exist." % input_directory
#             return
# 
#         print "* lophi.bat %s" % self.FTP_DIR
# 
#         if G.VERBOSE:
#             print "* Loading %s on %s..." % (input_directory, self.FTP_PATH)
# 
#         print "Getting script"
# 
# #        print self.config
# 
#         if self.config.volatility_profile is None:
#             print "ERROR: No profile provided for this machine.  Cannot execute code."
#             return
# 
#         # Get our script to execute
#         SCRIPT = S.get_execute_script(self.config.volatility_profile,
#                                             ftp_info,
#                                             self.FTP_DIR)
# 
#         # Clear our ftp directory
#         if os.path.exists(self.FTP_PATH):
#             shutil.rmtree(self.FTP_PATH)
# 
#         # Copy new contents
#         shutil.copytree(input_directory, self.FTP_PATH)
# 
#         # Start emulating 
#         DOM = self._connect()
#         # Get terminal
#         if G.VERBOSE:
#             print "* Opening terminal"
# 
#         if SCRIPT["HOTKEY"]:
#             DOM.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 0, SCRIPT["HOTKEY"], len(SCRIPT["HOTKEY"]), 0)
# 
#         time.sleep(1)
#         # Open Run Dialog
#         for command in SCRIPT["COMMANDS"]:
#             if G.VERBOSE:
#                 print "* Typing: %s" % command
# 
#             for c in command:
#                 DOM.sendKey(libvirt.VIR_KEYCODE_SET_LINUX, 0, [c], 1, 0)
#                 time.sleep(.1)
# 
#             time.sleep(1)
# 
#         self._disconnect()
#         
        
#     def attach_usb(self, input_directory):
#         """
#             This will create a USB device with the contents from 
#             'input_directory' and attach it to the machine
#             
#             # set size of disk
#             dd if=/dev/zero of=usb_${sizeMB}.img bs=512 count=$size
#             # equivalent to: qemu-img create -f raw harddisk.img 100M
#             sudo parted usb_${sizeMB}.img mktable msdos
#             # create partition table
#             sudo parted usb_${sizeMB}.img "mkpart p fat32 1 -0"
#             # make primary partition, type fat32 from 1 to end
#             sudo parted usb_${sizeMB}.img mkfs y 1 fat32
#             # list partition table (in bytes)
#             offset=$(parted harddisk.img unit b print | tail -2 | head -1 | cut -f 1 --delimit="B" | cut -c 9-)
#             
#             sudo mount -a -o loop,offset=$offset usb_${sizeMB}.img usb0/
#         """
# 
# 
# 
#         min_size = 2 ** 20 * 100 # 100MB
#         input_size_b = min_size # max(min_size, G.get_directory_size(input_directory))
#         input_size_mb = input_size_b / (2 ** 20)
# 
#         # Keep some extra space
# #        input_size_mb = input_size_mb * (2)
# 
#         print "* Creating a %dMB USB Key..." % input_size_mb
# 
#         input_size_mb = (input_size_mb * 1024 * 1024) / 512
#         # Create img
# 
#         call(["dd",
#               "if=/dev/zero",
#               "of=%s" % self.USB_IMG,
#               "bs=512",
#               "count=%d" % input_size_mb])
# 
#         print "* Formating image (msdos)..."
#         # Format  (-s for script)
#         call(["parted", "-s", self.USB_IMG, "mktable msdos"])
# 
#         print "* Formating image (fat32)..."
#         call(["parted", "-s", self.USB_IMG, "mkpart p fat32 1 -0"])
# 
#         print "* Formating image (fat32)..."
#         call(["parted", self.USB_IMG, "mkfs y 1 fat32"])
# 
#         # Get our offset.  (Should be a nicer way...)
#         import subprocess
# #        offset = subprocess.check_output("parted harddisk.img unit b print | tail -2 | head -1 | cut -f 1 --delimit=\"B\" | cut -c 9-")
#         ## TODO: Make dynamic
#         offset = 1048576
# 
#         print "* Mounting image..."
#         # Mount image
#         call(["mount",
#               "-a", # Mount all
#               "-oloop,offset=%d" % offset, # Loopback and size
#               self.USB_IMG,
#               self.USB_PATH
#               ])
# 
#         # Copy contents
#         print "* Copying contents to USB..."
# 
#         G.copy_tree(input_directory, self.USB_PATH)
# #        call(["cp", "-r", os.path.join(input_directory, "/*"), self.USB_PATH])
# 
#         # Unmount image
#         call(["umount", self.USB_PATH])
# 
#         print "* Attaching device..."
#         # Finally, attach to the VM
#         DOM = self._connect()
# 
#         usb_xml = self.USB_XML.replace(REPLACE_STRINGS.usb_img, self.USB_IMG)
#         DOM.attachDevice(usb_xml)
# 
#         self._disconnect()
#     
#         
#     def detach_usb(self):
#         """
#             Detach and attached USB device.
#         """
#         rtn = True
# 
#         DOM = self._connect()
# 
#         try:
#             usb_xml = self.USB_XML.replace(REPLACE_STRINGS.usb_img, self.USB_IMG)
#             DOM.detachDevice(usb_xml)
#         except:
#             rtn = False
#             pass
# 
#         self._disconnect()
# 
#         return rtn