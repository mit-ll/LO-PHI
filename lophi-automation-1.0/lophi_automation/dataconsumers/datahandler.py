"""
    This is a very simple class to relay data between source and consumers.
    
    (c) 2015 Massachusetts Institute of Technology
"""

#
import logging
logger = logging.getLogger(__name__)

# Native
import multiprocessing

# LO-PHI
import lophi.globals as G
import lophi_automation.protobuf.helper as protobuf

class DataHandler(multiprocessing.Process):
    """
        This class is simply an amplifier.  It reads input on 1 input queue 
        and replays it to all of the other data queues.
    """

#    INPUT_QUEUE = None


    def __init__(self, input_queue):
        """ Just save our queue """

        self.INPUT_QUEUE = input_queue
        self.OUTPUT_QUEUES = []

#        threading.Thread.__init__(self)
        multiprocessing.Process.__init__(self)

    def add_queue(self, queue):
        """ add new output to our list """

        self.OUTPUT_QUEUES.append(queue)


    def new_queue(self):
        """ create a new queue, append it, and return it """

        output_queue = multiprocessing.Queue()

        self.OUTPUT_QUEUES.append(output_queue)

        return output_queue


    def run(self):
        """
            Loop forever consuming data
        """
        if len(self.OUTPUT_QUEUES) == 0:
            return


        # Wait for output to start returning, and handle appropriately
        while True:

            # Read our input
            try:
                output = self.INPUT_QUEUE.get()
            except:
                print "ERROR/DataHandler: Queue failed to get data."
                break

            if output == G.CTRL_CMD_KILL:
                output_packed = output
            else:
                output_packed = protobuf.pack_sensor_output(output)

            # If its a kill command, die
            if output == G.CTRL_CMD_KILL:
                if G.VERBOSE:
                    print "Killing Data Handler..."
                for q in self.OUTPUT_QUEUES:
                    q.put(None)
                    q.close()
#                self.INPUT_QUEUE.close()
                break

            # Forward it
            for q in self.OUTPUT_QUEUES:
                q.put(output_packed)


        logger.debug("Data Handler Closed")

#        self.INPUT_QUEUE.close()

        import sys
        sys.exit(0)
        
    def stop(self):
        
        logger.debug("Killing data handler.")
        
        # Terminate process
        self.terminate()
            
        

