DIR_ROOT = "/opt/lophi"
DIR_BINARY_FILES = "bin"
DIR_CONFIG = "conf"
DIR_TFPBOOT = "tftpboot"

# PXE/DHCP/DNS
CONFIG_NETWORK = "network.conf"
# Mapping of images
CONFIG_IMAGES = "images_map.conf"

"""
    Database and Incoming FTP Server Settings
"""
# DB parameters
DB_URI = 'mongodb://localhost:27017/lophi_db'
SAMPLES_COLLECTION_URI = DB_URI+'/samples' # where the binaries are stored and other data
ANALYSES_COLLECTION_URI = DB_URI+'/analyses' # analyses files, e.g. memory dumps, disk logs, etc.


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

def print_traceback():
    import sys, traceback
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print "*** print_exception:"
    traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=2, file=sys.stdout)
