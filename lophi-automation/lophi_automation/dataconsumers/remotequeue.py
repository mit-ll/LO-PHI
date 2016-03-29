"""
    Unused classes for handling remote queues

    (c) 2015 Massachusetts Institute of Technology
"""
import socket
import time
import multiprocessing


import lophi.globals as G
import lophi_automation.protobuf.helper as ProtoBuf

class ClientRelay(multiprocessing.Process):
    """
        Small subclass that simply relays and object from socket to queue
    """

    def __init__(self, sock, addr, queue):
        """ Rember our socket """
        self.SOCK = sock
        self.address = addr
        self.OUTPUT_QUEUE = queue
        self.RUNNING = True
        multiprocessing.Process.__init__(self)

    def cleanup(self, sig, func=None):
        """ Cleanup our children and our sockets nicely """

        # Stop exectution
        self.RUNNING = False

        # Shtudown our socket
        self.SOCK.shutdown(socket.SHUT_RDWR)

        # Kill our queue        
        self.OUTPUT_QUEUE.cancel_join_thread()
        self.OUTPUT_QUEUE.close()

    def run(self):
        """ Loop until we fail relaying objects """

        # Set our handler to close gracefully        
        G.set_exit_handler(self.cleanup)

        if G.VERBOSE:
            print "Relaying data from socket to queue."

        while self.RUNNING:

            # Try to unpack it
            try:
                # Get our data
                data = G.read_socket_data(self.SOCK)

                # Unpack our sensor output
                data = ProtoBuf.unpack_sensor_output(data)

            except EOFError:
                if G.VERBOSE:
                    print "RemoteQueue: Looks like our socket closed."

                break
            except:
                # Just die!
                if self.RUNNING:
                    print "ERROR/RemoteQueue: Could not unpickle network data."

                break

            # update our machine name to indicate its origin
            data['MACHINE'] = self.address[0] + "-" + data['MACHINE']

            # Write the data to our queue, if we can
            try:
                self.OUTPUT_QUEUE.put(data, False)
            except:
                if self.RUNNING:
                    print "ERROR/RemoteQueue: Could not write to output queue."
                G.print_traceback()
                break

        # Close socket
        self.SOCK.close()




class RemoteQueueServer(multiprocessing.Process):
    """
        This class handles receiving objects over the network for us.
    """

    def __init__(self, output_queue):
        """ Remember the socket that we are relaying data to """

        self.RUNNING = True

        multiprocessing.Process.__init__(self)

        self.OUTPUT_QUEUE = output_queue

        self.clients = []


    def cleanup(self, sig, func=None):
        """ Cleanup our children and our sockets nicely """

        if G.VERBOSE:
            print "Shutting down nicely..."

        # Kill all spawned threads
        for c in self.clients:
            c.terminate()
            c.join()

        # Close up shop
        self.SOCK.shutdown(socket.SHUT_RDWR)
        self.SOCK.close()

        # Stop Execution
        if G.VERBOSE:
            print "Closing..."
        self.RUNNING = False


    def run(self):
        """ Bind a socket, and accept connections that send pickled objects """


        # Set our handler to close gracefully        
        G.set_exit_handler(self.cleanup)

        # Open our socket
        self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Ignore the silly TIME_WAIT state
        self.SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to our address/port
        BOUND = False
        while not BOUND:
            try:
                self.SOCK.bind(G.QUEUE_ADDR)
                BOUND = True
            except:
                print "RemoteQueue: Cannot bind socket... (Retrying in %d seconds)" % G.LOPHI_BIND_RETRY
                time.sleep(G.LOPHI_BIND_RETRY)

        # Listen for a client (Only 1 at a time)
        self.SOCK.listen(2)

        if G.VERBOSE:
            print "RemoteQueue: Listening on %s:%s..." % (G.QUEUE_ADDR[0], G.QUEUE_ADDR[1])


        while self.RUNNING:
            try:
                clientsock, addr = self.SOCK.accept()
                if G.VERBOSE:
                    print "RemoteQueue: Got connection from %s:%s." % (addr[0], addr[1])
                client = ClientRelay(clientsock, addr, self.OUTPUT_QUEUE)
                client.start()
                self.clients.append(client)
            except:
                break

        if G.VERBOSE:
            print "RemoteQueue: Closed"



class RemoteQueueClient(multiprocessing.Process):
    """ This will take a queue as input and relay across a socket """

    def __init__(self, input_queue, remote_addr):
        """ Remember input and store our remote socket info """
        self.INPUT_QUEUE = input_queue
        self.sock_addr = (remote_addr[0], G.QUEUE_PORT)
        self.RUNNING = True
        self.cache = {}
        multiprocessing.Process.__init__(self)


    def connect(self):
        """ Connect to our remote host """
        while 1:
            try:
                if G.VERBOSE:
                    print "RemoteQueue: Connecting to %s:%d..." % (self.sock_addr[0], self.sock_addr[1])
                # Open our socket
                self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                self.SOCK.connect(self.sock_addr)

                break
            except socket.error:
                if G.VERBOSE:
                    print "RemoteQueue/WARNING: Couldn't connect to %s:%d, retrying in %d seconds..." % (self.sock_addr[0], self.sock_addr[1], G.LOPHI_SOCKET_RETRY)
                time.sleep(G.LOPHI_SOCKET_RETRY)
                continue

    def cleanup(self, sig, func=None):
        """ Cleanup our children and our sockets nicely """

        # Close our socket nicely
        self.SOCK.close()
        self.INPUT_QUEUE.close()
        self.RUNNING = False

    def run(self):
        """ Loop forever sending data that is sent in on the queue """

        # Set our handler to close gracefully        
        G.set_exit_handler(self.cleanup)

        # Connect to remote host
        self.connect()

        if G.VERBOSE:
            print "Starting RemoteQueue Client..."

        # loop forever
        while self.RUNNING:
            # Get our data
            try:
                data = self.INPUT_QUEUE.get()
            except:
                if G.VERBOSE:
                    print "WARNING: Could not get data from queue!"
                pass

            if data == G.CTRL_CMD_KILL:
                break

            ###
            ##    TODO : Optimization!!!
            ###

            # Extract index info
#            machine = data['MACHINE']
#            name = data['SUA_NAME']
#            profile = data['SUA_PROFILE']
            module = data['MODULE_NAME']

            pb2_data = ProtoBuf.pack_sensor_output(data)


            # Is this something new?  If not lets not waste the bandwidth
            if module not in self.cache or self.cache[module] != data:
                self.cache[module] = data
            else:
                continue

            # Try to write it to our socket
            while True:
                try:

                    G.send_socket_data(self.SOCK, pb2_data)

                    break
                except:
                    if G.VERBOSE:
                        print "RemoteQueueClient: Socket Closed."
                    # Clear our cache and try to reconnect
                    del self.cache[module]
                    self.connect()

        # Close our socket nicely
        self.SOCK.close()


