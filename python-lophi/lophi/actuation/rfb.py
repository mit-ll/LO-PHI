"""
    This is a very simplistic VNC Client that only handles mouse pointer 
    movements.
    
    (c) 2015 Massachusetts Institute of Technology
"""
import time
import socket
import struct
import logging
logger = logging.getLogger(__name__)


BUFFER_SIZE = 1024

# Mouse button mappings
MOUSE_RIGHT = 0b100
MOUSE_LEFT = 0b1

class RFBClient():
    """
        Just a simple RFB implementation
    """
    
    def __init__(self,host="localhost", port=5900,connect=True):
        """
            Intiailize our connection to the VNC server
        """
        self.SOCK = None
        
        self.host = host
        self.port = port
        
        self.width = 0
        self.height = 0
        
        # Mouse functions
        self.buttons = 0b00000000
        self.x = 0
        self.y = 0
        
        if connect:
            self._initVNC()
        
        
    def _initVNC(self):
        """
            Initialize our VNC connection
        """
        logger.debug("Initializing VNC...")
        
        self._negotiateVersion()
        self._negotiateSecurity()
        self._shareDesktop()
        self._setEncodings()
        
    def _connect(self):
        """
            Just connect our TCP socket
        """
        if self.SOCK is not None:
            return True
        
        try:
            self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.SOCK.connect((self.host, self.port))
            return True
        except:
            logger.error("Couldn't connect to %s:%d"%(self.host,self.port))
            return False
        
    def _negotiateVersion(self):
        """
            Negotiate our version of RFB with the server
        """
        
        assert self._connect()
        
        server_ver_data = self.SOCK.recv(BUFFER_SIZE)
        server_version = server_ver_data.split()[1].split(".")
        
        # Let's just say we have whatever version the server has
        # Mouse commands have remained constant
        self.SOCK.sendall("RFB %s.%s\n"%(server_version[0],server_version[1]))

    def _negotiateSecurity(self):
        """    
            Negotiate the security of this connection
        """
        
        assert self._connect()
        
        security_data = self.SOCK.recv(BUFFER_SIZE)
        
        # length (byte) | types (1 byte each)
        security_types = struct.unpack("%dB"%len(security_data),security_data)
        
        # Make sure None (1) is an available option.
        for i in range(security_types[0]):
            if security_types[i+1] == 1:
                # Send our selection
                self.SOCK.sendall("\x01")
                security_result = self.SOCK.recv(BUFFER_SIZE)
                return True
            
        logger.error("Server does not appear to support 'None' security.")
                
    def _shareDesktop(self,status=True):
        """
            Deterime if we are sharing the desktop or taking exclusive access.
        """
        
        assert self._connect()

        if status:
            self.SOCK.sendall("\x01")
        else:
            self.SOCK.sendall("\x00")

    def _setEncodings(self, list_of_encodings=[-257]):
        """
            Set the encodings that we support
            -257 is the QEMU protocol
        """
        
        assert self._connect()

        # Construct our packet
        encoding_packet = struct.pack("!BxH", 2, len(list_of_encodings))
        encoding_packet += struct.pack("!%di"%len(list_of_encodings), *list_of_encodings)
        
        # Send our encodings        
        self.SOCK.sendall(encoding_packet)
    
    def _pointerEvent(self, x, y, buttonmask=0):
        """Indicates either pointer movement or a pointer button press or release. The pointer is
           now at (x-position, y-position), and the current state of buttons 1 to 8 are represented
           by bits 0 to 7 of button-mask respectively, 0 meaning up, 1 meaning down (pressed).
        """
        
        assert self._connect()
        
        self.SOCK.send(struct.pack("!BBHH", 5, buttonmask, x, y))

    def mouseMove(self,x,y):
        """
            Move a mouse to absolute position (x,y)
        """
        logger.debug("mouseMove (%d,%d)"%(x,y))
        
        # Save our coordinates and move the mouse
        (self.x, self.y) = (x, y)
        self._pointerEvent(x, y, self.buttons)
        
        # Sleep a bit so the OS has time to register
        time.sleep(.05)
        
    def mouseClick(self,button=MOUSE_LEFT,double_click=False):
        """
            Click the mouse at the (x,y) coordinate the mouse was last moved to
        """
        
        logger.debug("mouseClick %s (double_click=%s)"%(button,double_click))
        
        if double_click:
            clicks = 2
        else:
            clicks = 1
        # Send a press, and then shortly after, release
        
        for i in range(clicks):
            self._pointerEvent(self.x, self.y, button)
            time.sleep(.01)#
            
            self._pointerEvent(self.x, self.y, 0)
            time.sleep(.01)