"""
    Lots of useful globals for LO-PHI code.  Everything should be good to go
    off the bat, but its all here if you need to change anything.

    (c) 2015 Massachusetts Institute of Technology
"""
import os
import logging
logger = logging.getLogger(__name__)

"""
    Basic LO-PHI Configuration
"""
DEBUG = False
VERBOSE = True



# Logging
LOG_DIR = "lophi_logs/"
DEFAULT_LOG_FILE = "lophi.log"

# Networking
MAX_PACKET_SIZE = 65516
UDP_RECV_BUFFER_SIZE = 0x7fffffff

# Server Parameters
LOPHI_HOST = '0.0.0.0'
LOPHI_PORT = 1337
LOPHI_BUFFER = 1024
LOPHI_SOCKET_RETRY = 5

LOPHI_BIND_RETRY = 3
SLEEP_TIME_KILL = 5



# Directory structure
DIR_ROOT = "/lophi"
DIR_EXAMPLES = "examples"
DIR_VOLATILITY = "volatility"
DIR_ACTUATION_SCRIPTS = "actuation_scripts"
DIR_BINARY_FILES = "bin"
DIR_CONFIG = "conf"
DIR_ANALYSIS_SCRIPTS = "analysis_scripts"
DIR_TOOLS = "tools"
DIR_SCRIPTS = "scripts"
DIR_TFPBOOT = "tftpboot"
DIR_TMP = "tmp"
DIR_DISK_SCANS = "disk_scans"
DIR_DISK_IMAGES = "disk_images"

#FTP Info
FTP_PORT = 2121
FTP_USER = "lophi"
FTP_PASSWORD = "1lophiihpol2"
FTP_ROOT = DIR_ROOT+'/ftp'


# Volality configs
DEFAULT_VOLATILITY_DIR = "Volatility-1.4_rc1"

# Master Config
CONFIG_MASTER = "controllers.conf"
# Sensor Config
CONFIG_SENSORS = "sensors.conf"
# Machines
CONFIG_MACHINES = "machines.conf"
# PXE/DHCP/DNS
CONFIG_NETWORK = "network.conf"
# Mapping of images
CONFIG_IMAGES = "images_map.conf"


DIR_VM_OUTPUT = "vms"
IMG_SUBDIR_ORIG = "imgs_orig"
IMG_SUBDIR = "ramdisk"
CONFIG_SUBDIR = "confs"
SNAPSHOT_DIR = "snapshots"
DISK_SCAN_SUBDIR = "disk_scans"
FTP_SUBDIR = "ftp"
FTP_NUM = 0

RAMDISK = IMG_SUBDIR


CARD_REG_PORT = 1339

# CTRL Type parameters for messages to LOPHI Master
CTRL_TYPE = 'ctrl'
REG_TYPE = 'reg'



# PYBOOTD SERVER SETTINGS
PXE_DEFAULT_IP = "localhost"
PXE_BOOT_PORT = 67
PXE_ACL_PORT = 4011
PXE_HEADER_LEN = 6
PXE_ADD_ACL = "addacl"
PXE_SET_CONF = "addpxe"
PXE_DEL_ACL = "delacl"
PXE_GET_IP = "getip"
PXE_OK_RESP = "OK"
PXE_NO_IP_RESP = "NO_IP"


"""
    RabbitMQ
"""
QUEUE_PORT = 1338
QUEUE_ADDR = (LOPHI_HOST, QUEUE_PORT)

# RabbitMQ Parameters
class RabbitMQ:
    AMQP_HOST = "localhost"
    # Exchanges
    EXCHANGE_DIRECT = 'lophi.direct'
    EXCHANGE_TOPIC = 'lophi.topic'
    EXCHANGE_FANOUT = 'lophi.fanout'
    # Queues
    CTRL_IN = 'lophi.control-in'
    CTRL_OUT = 'lophi.control-out'
    SENSOR = 'lophi.sensor'
    REGISTER = 'lophi.reg'
    # Types
    TYPE_TOPIC = "topic"
    TYPE_FANOUT = "fanout"


"""
    Actuation Settings
"""

SUT_ANALYSIS_PORT = 31333

# Map profiles to their ftp actuation script
PROFILE_TO_SCRIPT = { "WinXPSP3x86": "windows.act",
                      "Win7SP0x86": "win7.act",
                      "Win7SP0x64": "win7.act"}
        


"""
    Database and Incoming FTP Server Settings
"""
# DB parameters
DB_HOST = 'localhost'
DB_URI = 'mongodb://localhost:27017/lophi_db'
DB_SAMPLES = '/samples' # where the binaries are stored and other data
DB_ANALYSES = '/analyses' # analyses files, e.g. memory dumps, disk logs, etc.

# Where we store binaries and analysis data  (These are subdirectories under FTP_ROOT
UPLOAD_FILE_ROOT = 'files'
BINARY_FILE_ROOT = 'binaries'
ANALYSIS_FILE_ROOT = 'analysis'

# JOB Status
JOB_QUEUED = 'QUEUED'
JOB_RUNNING = 'RUNNING'
JOB_DONE = 'COMPLETED'
JOB_FAILED = 'ERROR'
JOB_UNKNOWN = 'UNKNOWN'




"""
    Physical Sensor Settings
"""

class SENSOR_TYPES:
    MEMORY = 0
    DISK = 1
    CONTROL = 2
    CPU = 3
    NETWORK = 4
    
    
# set this to set the minimum packet length for the UDP command packets
MIN_UDP_SIZE = 64 # bytes

class SENSOR_MEMORY:
    DEFAULT_IP = "172.20.1.11"
    DEFAULT_PORT = 31337
    
    DEFAULT_NODE = 0x00000000
    DEFAULT_FLAGS = 0x00000000
    
    MAGIC_LOPHI = 0xDEADBEEF

    class COMMAND:
        PING = 10
        READ = 0
        RAPID_COMMAND_ADDR = 5
        WRITE = 2
        SUB = 3
        RAPID_COMMAND_SUB = 7
        UNSUB = 4
        RAPID_COMMAND_UNSUB = 8
        LIST = 5
        LOPHI_UPDATE_NOTICE = 6
        SEARCH = 7
        DEBUG = 253
        LOG = 254
        VERSION = 255
    


class SENSOR_CPU:
    DEFAULT_IP = "172.20.1.200"
    DEFAULT_PORT = 31337


class SENSOR_CONTROL:
    # Try to act like a human
    SLEEP_INTER_KEY = .01
    SLEEP_INTER_CMD = .5
    # Command Types
    ON_CMD = "ON "       # TURN ON
    OFF_CMD = "OFF"      # TURN OFF
    SHUTDOWN_CMD = "SHU" # Shutdown machine nicely
    RESET_CMD = "RST"    # Hard reset the machine
    KEYB_CMD = "KEY"     # TYPE via keyboard
    KEY_SP_CMD = "KSP"   # Special keyboard commands
    KEY_SLEEP = "SLP"    # Just sleep for the amount of time
    MOUSE_CMD = "MOU"    # USE MOUSE
    MOUSE_WIGGLE = "WGL"
    STATUS_CMD = "STA"   # Get status of the machine power (Up/Down)
    RESTART_CMD = "DIE"  # Reset the hardware
    # Command Message Structure is
    # <CMD>:<PAYLOAD>
    # End character for msg
    END_MSG = chr(3)
    # End character for transmission
    END_TRANSMISSION = chr(4)
    # Registration, Deregistration, and Querying   
    REG_LEN = 4
    REG_CMD = "REG "
    DEREG_CMD = "DREG"
    # TODO: make this command more sophisticated so we can call other functions?
    QUERY_CMD = "QUER"

    RESPONSE_DONE = "DONE"
    
    # LOPHI port
    DEFAULT_PORT = 1440
    DEFAULT_IP = "172.20.1.20"
    
    class POWER_STATUS:
        ON = "ON"
        OFF = "OFF"
        UNKNOWN = None
    

class SENSOR_DISK:
    # What link type should we put in our pcap header?
    PCAP_TYPE = 255

    MAGIC_LOPHI = 0xDEADBEEF

    # NETWORK OP CODES
    class OP:
        REG_READ = 0x0
        REG_WRITE = 0x01
    
        SATA_FRAME = 0x80
    
        QUERY_CARDS = 0x0d
        REGISTER_CARD = 0x0e
        UNREGISTER_CARD = 0x0f
        
    class ADDR:
        """ Address on the sensor for different register values """
        VERSION = 0x00
        UDP_DELAY = 0x01
        MAC_SENS = 0x02
        IP_SENS = 0x04
        MAC_DEST = 0x06
        IP_DEST = 0x08
        UDP_DEST_PORT = 0x09
        MTU_SIZE = 0xa
        # SATA
        SATA_CTRL = 0x10
        
    # Defaults    
    DEFAULT_IP = "172.20.1.1"
    DEFAULT_PORT = 31337
    DEFAULT_SECTOR_SIZE = 512
        
        
# SATA Operations
# TODO: Verify these!?
class SATA_OP:
    class DIRECTION:
        READ = 0x00
        WRITE = 0x01

    READ_META = 0x01
    WRITE_META = 0x02

    READ_CONTENT = 0x03
    WRITE_CONTENT = 0x04

    CREATION = 0x05
    DELETION = 0x06

    MOVED = 0x07

    READ_MBR = 0x08
    WRITE_MBR = 0x09

    TIMESTAMP = 0x0a

    HIDDEN = 0x0b
    UNHIDDEN = 0x0c

    READ_UNKNOWN = 0x0d
    WRITE_UNKNOWN = 0x0e
        


"""
    GUI Parameters
"""
GUI_WIDTH = 850
GUI_HEIGHT = 1000
# Graph size (inches)
FIG_WIDTH = 10
FIG_HEIGHT = 10
GRAPH_REFRESH_RATE = 1 # sec



"""
    Globals to keep track of the state of the machine.
"""

# Note the indicies must be the proper position.  Just a hack for now, will fix later
## TODO: Better ENUMS
MACHINE_STATES = {'OFF'         :0,
                 'STARTED'      :1,
                 'SNAPSHOTTING' :2,
                 'RESTORING'    :3,
                 'RESUMING'     :4,
                 'PAUSED'       :5,
                 'UNKNOWN'      :6

                 }
DISK_STATES = {'REVERTED'       :0,
               'DIRTY'          :1,
               'UNKNOWN'        :2
               }
# Settings for Machine Types
class MACHINE_TYPES:
    PHYSICAL = 0
    XEN = 1
    KVM = 2
    ANY = 10
    ASCII = {PHYSICAL   :"Physical",
             XEN        :"Xen VM",
             KVM        :"Qemu-KVM"}

"""
        Xen Global Settings
"""

# Globals for generating VM images
VM_FILLIN_CHAR = "??"                   # ??'s are filled in appropriately
VM_NAME_TEMPLATE = "lophi-??"
VM_MAC_TEMPLATE = "00:16:3e:d7:8f:??"
VM_DISK_TEMPLATE = "lophi-img-??.qcow2"
VM_DISK_BASE_TEMPLATE = "lophi-img-??.img"


# Default snapshot Configs
SNAPSHOT_SLEEP_DEFAULT = 60 * 3 # 3 minutes




"""
    Global commands used between the controller and analysis engines
"""
# Special
CTRL_CMD_MACHINE_CONF = "machine_config_update"

# User Input
CTRL_CMD_PAUSE = "pause"
CTRL_CMD_UNPAUSE = "resume"
CTRL_CMD_START = "start"
CTRL_CMD_RUN = "run"
CTRL_CMD_STOP = "stop"
CTRL_CMD_KILL = "kill"
CTRL_CMD_LIST = "list"
CTRL_CMD_DIE = "die"
CTRL_CMD_PICKLE = "pickle"
CTRL_CMD_DONE = "!?DONE?!"
CTRL_CMD_UPDATE_HW = "update hw"
CTRL_CMD_SPLASH = "splash"
CTRL_CMD_ATTACH = "attach"
CTRL_CMD_EXECUTE = "execute"
CTRL_CMD_HELP = "help"

# Special Strings for the controller
RECV_PROFILE_NAME = "pickle_profile" # this means we'll push a profile using pickle


try:
    import libvirt
    LIBVIRT_STATES = {
        libvirt.VIR_DOMAIN_NOSTATE: 'no state',
        libvirt.VIR_DOMAIN_RUNNING: 'running',
        libvirt.VIR_DOMAIN_BLOCKED: 'blocked on resource',
        libvirt.VIR_DOMAIN_PAUSED: 'paused by user',
        libvirt.VIR_DOMAIN_SHUTDOWN: 'being shut down',
        libvirt.VIR_DOMAIN_SHUTOFF: 'shut off',
        libvirt.VIR_DOMAIN_CRASHED: 'crashed',
    }
except:
    LIBVIRT_STATES = {}
    pass


"""
    Useful global functions
"""

def dir_create_tmp(mode=0775):
    """
        Create a tmp directory to store analysis data
    """
    import uuid
    tmp_dir = os.path.join(DIR_ROOT,DIR_TMP,str(uuid.uuid1()))
    try:
        os.makedirs(tmp_dir, mode)
        return tmp_dir 
    except:
        logger.error("Could not create tmpt directory. (%s)"%tmp_dir)
        return None
    
def dir_remove(rm_dir):
    """
        Recursively remove all files in the specified directory
    """
    import shutil
    
    try:
        shutil.rmtree(rm_dir)
        return True
    except:
        return False

def ensure_dir_exists(f):
    d = os.path.dirname(f)
    if d != "" and not os.path.exists(d):
        try:
            os.makedirs(d)
        except:
            pass

def get_datestamp():
    from time import strftime
    return strftime("%Y_%m_%d-%H%M%S")

def get_username_local():
    import getpass
    import socket
    
    return getpass.getuser()+"@"+socket.gethostname()

def set_exit_handler(func):
    import sys
    import os
    if os.name == "nt":
            try:
                import win32api
                win32api.SetConsoleCtrlHandler(func, True)
            except ImportError:
                version = ".".join(map(str, sys.version_info[:2]))
                raise Exception("pywin32 not install for Python " + version)
    else:
        import signal
        signal.signal(signal.SIGTERM, func)

#
# Controller functions for pretty output
#
def print_machines(tmp_list):
    """ Simple function to print our list of machines """
    output = "   Machine Name  : Machine Type :        Profile        :       CPU       :       Disk      :      Memory     :      Control \n"
    output += "-"*130
    output += "\n"
    for i in tmp_list:
        x = tmp_list[i]
        t = MACHINE_TYPES.ASCII[x.type]
        
        cpu = disk = memory = control = ""
        
        output += " %15s : %12s : %21s : %15s : %15s : %15s : %15s\n" % (x.config.name.encode("ascii"),
                                           t,
                                           x.config.volatility_profile.encode("ascii"),
                                           cpu,
                                           disk,
                                           memory,
                                           control)
        
    if len(tmp_list) == 0:
        output += "No machines are loaded.\n"
    output += "-"*130
    output += "\n"
    return output.encode("ascii",'ignore')

def print_analyses(tmp_list):
    """ Simple function to print our list of running analyses """
    output = "  ID  :   Config Name   :   Machine Name  : Machine Type :        Profile        :          Created\n"
    output += ("-"*110) + "\n"
    for i in tmp_list:
        x = tmp_list[i]

        from datetime import datetime
        from lophi.protobuf.analysis_pb2 import AnalysisInfo

        if isinstance(x, AnalysisInfo):
            # If its not pickled we can just access the classes directly
            ae_id = x.analysis_id
            created = x.created
            lophi_name = x.lophi_name
            machine_name = x.machine_name
            t = x.machine_type
            profile = x.volatility_profile

            ts = datetime.fromtimestamp(created)
        else:
            # To pickle we have to pass it as a dict
            ae_id = i
            lophi_name = x['lophi_name']
            created = x['created']
            t = MACHINE_TYPES.ASCII[x['machine_type']]
            machine_name = x['machine_name']
            profile = x['volatility_profile']
            ts = datetime.fromtimestamp(created)

        output += " %4s : %15s : %15s : %12s : %21s : %s\n" % (str(ae_id),
                                                             lophi_name,
                                                             machine_name,
                                                             t,
                                                             profile,
                                                             ts)
    if len(tmp_list) == 0:
        output += "There are no analyses running.\n"
    output += ("-"*110) + "\n"
    return output

# Colors!
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''

def ramdisk_status(path):
    """
        Will return the total, used, and free space in our ramdisk
    """
    import os
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return (total, used, free)


def ramdisk_check(ram_path, mount=False, size="10G"):
    """
        Check to see if our ramdisk was created, and potentially create it.
        
        This is used for storing our qcow2 images efficiently
        
    """
    import os
    from subprocess import call

    if os.path.ismount(ram_path):
        return True
    elif mount:
        if not os.path.exists(ram_path):
            os.makedirs(ram_path, 0755)
        cmd = ["mount", "-ttmpfs", "-osize=%s" % size, "tmpfs", ram_path]
        call(cmd)
    return False



def get_directory_size(path):
    """
        This will return the filesize in bytes of the contents in 'path'
    """
    import os
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def copy_tree(src, dst):
    """
        Copy an entire directory tree from src to dst
    """
    import shutil, os

    names = os.listdir(src)

    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        if os.path.isdir(srcname):
            shutil.copytree(srcname, dstname)
        else:
            shutil.copy2(srcname, dstname)
    shutil.copystat(src, dst)

def volatilty_to_str(a):
    """
        This function is used within volatility modules to convert all output to
        strings
        
        @TODO Use latin1 decode and utf8 encode?
    """
    try:
        return str(a).decode("latin1").encode("utf8")
    except:
        return "??Could not Decode??"

def get_traceback():
    import sys, traceback
    exc_type, exc_value, exc_traceback = sys.exc_info()

    o = ""
    o += "*** Exception:"
    for x in traceback.format_exception(exc_type, exc_value, exc_traceback,
                              limit=2):
        o += x
    o += "*** Exec:"
    o += traceback.format_exc()
    
    return o

def print_traceback():
    import sys, traceback
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print "*** print_exception:"
    traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=2, file=sys.stdout)
    print "*** print_exc:"
    traceback.print_exc()

def send_socket_data(sock, data):
    """
        Given a socket and some data, this will prefix the length of the data
        and send it using the socket.
    """
    # Put data in a network format
    import struct
    data = struct.pack("H", len(data)) + data

    # Send the data
    sent = 0
    while sent < len(data):
        sent += sock.send(data[sent:])


def read_socket_data(sock):
    """
        Given an open socket will receive the next packet off the line
    """
    # Init our buffers
    data = ""
    tmp = ""

    # Get the size of the expected data
    import struct
    size = sock.recv(2)
    if len(size) == 0:
        return None
    size = struct.unpack("H", size)[0]

    # Read in all of the sent data
    while len(data) < size:
        tmp = sock.recv(size - len(data))
        if not tmp:
            return None

        data += tmp

    # Return the data
    return data


def flip_endianess(data):

    # Flip endianess!
    data2 = ""
    for i in range(len(data) / 4):
        tmp = data[i * 4:i * 4 + 4]
        data2 += tmp[3]
        data2 += tmp[2]
        data2 += tmp[1]
        data2 += tmp[0]

    return data2



def get_hex(input_list):
    """
        Convert a list of bytes into hex string
    """
    o = ""
    for i in input_list:
        o += "%02X"%ord(i)
    return o


def generate_dict(keys,values):
    rtn = {}
    for x in range(len(keys)):
        key = keys[x]
        value = values[x]
        rtn[key] = value 
    return rtn

def get_random_chars(y):
    import string
    import random
    return ''.join(random.choice(string.ascii_letters) for x in range(y))
