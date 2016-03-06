"""
    Class for handling configuration files for controller nodes

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import socket
import logging
logger = logging.getLogger(__name__)
from time import sleep


# LO-PHI
import lophi.globals as G
# LO-PHI Automation
import lophi_automation.protobuf.helper as ProtoBuf
from lophi_automation.configs import LophiConfig
from lophi_automation.network.command import LophiCommand

SOCKET_RETRY = 5

class ControllerConfig(LophiConfig):
    """
        Very simple class to hand around and leave room for improvement in the 
        future
    """

    def __init__(self, name, Config):
        """
            Initialize all of our variables and set any new settings that were
            specified in the config file.
        """

        # Some storage
        self.SOCK = None
        self.lophi_configs = None
        self.machines = None

        # Set our name
        self.name = name

        # Set our host
        if not self._get_option(Config, name, "host"):
            logger.error("No host ip provided for %s."%name)

        # Set our port
        if not self._get_option(Config, name, "port"):
            logger.error("No host port provided for %s."%name)

        # Make it easier when opening sockets
        self.address = (self.host, int(self.port))


    def __str__(self):
        """ Print out information of this controller """
        
        o = "[%s] IP: %s, Port: %s"%(self.name,self.host,self.port)
        
        return o

    def get_machines(self):

        """ Get protocol buffer version of remote machines """
        while 1:
            try:
                logger.debug("Getting machine list for Controller/%s" % self.name)

                # Get response
                cmd = LophiCommand(G.CTRL_CMD_PICKLE, args=["machines"])
                data = self.send_cmd(cmd)
                status = G.read_socket_data(self.SOCK)
                
                # Unpack our machine list 
                #    (WARNING: This a subset of the objects at the server
                if data is not None:
                    self.machines = ProtoBuf.unpack_machine_list(data)
                else:
                    self.machines = []

                return status
            except:
                G.print_traceback()
                self.connect()


    def get_analysis(self):
        """ Get protocol buffer version of remote analysis """
        while 1:
            try:
                logger.debug("Getting analysis list for Controller/%s" % self.name)
                    
                # Get reply
                cmd = LophiCommand(G.CTRL_CMD_PICKLE, args=["analysis"])
                analysis_buf = self.send_cmd(cmd)
                status = G.read_socket_data(self.SOCK)

                # unpack protocol buffer
                self.analysis = ProtoBuf.unpack_analysis_list(analysis_buf)

                return status
            except:
                self.connect()

    def connect(self):
        """
            Connect to our controller, retrieve all of the relevant information
            and add it to our list.
        """

        while 1:
            # Try forever to connect
            try:
                print G.bcolors.WARNING + "Connecting to %s(%s:%s)..." % (self.name, self.host, self.port) + G.bcolors.ENDC,
                # Open our socket
                self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                self.SOCK.connect(self.address)

                print G.bcolors.OKGREEN + "Connected." + G.bcolors.ENDC

                break
            except socket.error:
                print G.bcolors.FAIL \
                    + "Retrying in %d seconds..." % (SOCKET_RETRY) \
                    + G.bcolors.ENDC
                sleep(SOCKET_RETRY)
                continue

    def disconnect(self):
        """
            Stop all analysis at controllers and close our socket nicely
        """

        # Close socket
        self.SOCK.close()


    def send_analysis(self, filename, cmd):
        """ Sends start message and our JSON config """
        while 1:
            try:
                # Send our command to start the analysis
                G.send_socket_data(self.SOCK, str(cmd))

                # read our analysis file
                f = open(filename)
                script = f.read()
                f.close()

                # Send the json config
                G.send_socket_data(self.SOCK, script)

                status = G.read_socket_data(self.SOCK)
                
                return status
                
            except:
                self.connect()


    def send_cmd(self, command):
        """ Send arbitrary message """
        while 1:
            try:
                # Send our command to start the analysis
                G.send_socket_data(self.SOCK, str(command))

                # Get our return status       
                self.status = G.read_socket_data(self.SOCK)
                
                if self.status is None:
                    raise Exception("Controller Disconnected.")
                
                return self.status
            
            except:
                self.connect()


