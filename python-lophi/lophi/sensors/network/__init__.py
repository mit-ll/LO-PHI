"""
    Class for handling network data

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import multiprocessing
import logging
logger = logging.getLogger(__name__)

# 3rd Party
import pcap

# LO-PHI
from lophi.sensors import Sensor


class NetworkSensor(Sensor):
    """
        This implements a network sensor which will capture all of the observed
        into a pcap file.
    """
    
    def __init__(self,interface,name=None):
        """
            Initialize our sensor, which in this case is setting the interface 
            and any services/configurations on that interface.
        """
        self.interface = interface
        self.packet_cap = None
        if name is None:
            self.name = interface+"-NetworkSensor"
        else:
            self.name = name
        
        Sensor.__init__(self)
        
        
    def _connect(self):
        """
            Bind to an interface for sniffing
        """
        self.packet_cap = pcap.pcap(self.interface)
    
    
    def read(self):
        """
            Read the next packet off the wire
            
            @return: (timestamp, data) of the next network packet on the wire
        """
        if self.packet_cap is None:
            self._connect()
            
        return self.packet_cap.next() 
    
    
    def write(self,data):
        """
            Write a raw network packet to the wire
            
            @todo: Validate that this works!
        """
        self.packet_cap.inject(data)





class NetworkCapture(multiprocessing.Process):
    """
        Very simple class used to capture network traffic in a separate process
    """


    def __init__(self, machine, command_queue=None, output_queue=None):
        """
            Initialize our analysis engine
        """

        # Init our multiprocess
        multiprocessing.Process.__init__(self)

        # Save our machine
        self.machine = machine

        # Our queue to talk to the control program
        if output_queue is None:
            self.output_queue = multiprocessing.Queue()
        else:
            self.output_queue = output_queue

        # Our command queue
        if command_queue is None:
            self.command_queue = multiprocessing.Queue()
        else:
            self.command_queue = command_queue




    def run(self):
        """
            Capture packets from the wire and output them to our output queue
        """

        # Get data forever and report it back
        self.RUNNING = True
        self.PAUSED = False
        while self.RUNNING:

            try:
                cmd = self.command_queue.get(False).split(" ")
                logger.debug("Got cmd: %s" % cmd)
                if cmd[0] == G.CTRL_CMD_PAUSE:
                    logger.debug("Pausing analysis")
                    self.PAUSED = True

                if cmd[0] == G.CTRL_CMD_UNPAUSE:
                    logger.debug("Resuming Analysis")
                    self.PAUSED = False

                if cmd[0] == G.CTRL_CMD_KILL or cmd[0] == G.CTRL_CMD_STOP:
                    logger.debug("Got kill command")
                    self.RUNNING = False
                    break
            except:
                # Do nothing
                pass

            if self.PAUSED:
                time.sleep(1)
                continue

            # Get a network packet and return it over our output queue
            capture = self.machine.network_read()

            if capture is None:
                logger.error("No network data can be read.")
                break

            logger.debug("Read packet from wire. (%d bytes)"%len(capture[1]))

            # We have to convert to a byte string because buffer()'s cannot be
            # placed on queues. (Looks like a python bug
            capture = (capture[0],str(capture[1]))

            self.output_queue.put(capture)


            logger.debug("added packet to queue")

        logger.debug("Network Engine stopped.")

    def stop(self):
        """ Kill our process nicely """
        logger.debug("Killing network capture process...")
        self.output_queue.close()
        self.command_queue.close()
        self.terminate()