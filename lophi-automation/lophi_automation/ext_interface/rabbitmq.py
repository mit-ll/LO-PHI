"""
    Classes for handling RabbitMQ interactions

    (c) 2015 Massachusetts Institute of Technology
"""
# native
import multiprocessing
import json
import logging
import time


# RabbitMQ library
try:
    import pika
    HAS_PIKA = True
except:
    HAS_PIKA = False

# LO-PHI
import lophi.globals as G

LOG_FORMAT = ('[LOPHI RabbitMQ] %(levelname) -10s %(asctime)s %(name) -30s'
              '-5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class LOPHI_RabbitMQ():
    """
        This serves as the class to handle all RabbitMQ communication
    """
    def __init__(self, amqp_host):
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._host = amqp_host

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.

        :rtype: pika.SelectConnection

        """
        LOGGER.info('Connecting to %s', self._host)
        return pika.SelectConnection(pika.ConnectionParameters(self._host),
                                     self.on_connection_open)

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        LOGGER.info('Closing connection')
        self._connection.close()

    def add_on_connection_close_callback(self):
        """This method adds an on close callback that will be invoked by pika
        when RabbitMQ closes the connection to the publisher unexpectedly.

        """
        #LOGGER.info('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            #LOGGER.warning('Connection closed, reopening in 5 seconds: (%s) %s',
            #               reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def on_connection_open(self, unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection

        """
        LOGGER.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def reconnect(self):
        """Will be invoked by the IOLoop timer if the connection is
        closed. See the on_connection_closed method.

        """
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self._closing:

            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.

        """
        #LOGGER.info('Adding channel close callback')
#         if self.EXCHANGE_TYPE == G.RabbitMQ.TYPE_FANOUT:
#             self._channel.add_on_close_callback(self.on_channel_closed_3_arg)
#         else:
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed_2_arg(self, channel, **kargs):
        """
            Same as on_channel_closed but without extra args

        :param pika.channel.Channel: The closed channel

        """
        #LOGGER.warning('Channel %i was closed: (%s) %s',
        #               channel, reply_code, reply_text)
        self._connection.close()
        
    def on_channel_closed_3_arg(self, channel, unknown):
        """
            Same as on_channel_closed but without extra args

        :param pika.channel.Channel: The closed channel

        """
        #LOGGER.warning('Channel %i was closed: (%s) %s',
        #               channel, reply_code, reply_text)
        self._connection.close()


    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed

        """
        #LOGGER.warning('Channel %i was closed: (%s) %s',
        #               channel, reply_code, reply_text)
        self._connection.close()

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object

        """
        LOGGER.info('Channel opened')
        self._channel = channel
        
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.

        :param str|unicode exchange_name: The name of the exchange to declare

        """
        #print "Declaring exchange %s of type %s" % (exchange_name, self.EXCHANGE_TYPE)
        LOGGER.debug('Declaring exchange %s', exchange_name)
        self._channel.exchange_declare(callback=self.on_exchange_declareok,
                                       exchange=exchange_name,
                                       type=self.EXCHANGE_TYPE)

    def on_exchange_declareok(self, unused_frame):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame

        """
        LOGGER.info('Exchange declared')
        self.setup_queue(self.QUEUE)


    def setup_queue(self, queue_name):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command. When it is complete, the on_queue_declareok method will
        be invoked by pika.

        :param str|unicode queue_name: The name of the queue to declare.

        """
        #print "RabbitMQ: Declaring queue %s exclusive: %s, auto_delete: %s" % (queue_name, self.exclusive_queue, self.auto_delete)
        LOGGER.info('Declaring queue %s', queue_name)
        self._channel.queue_declare(callback=self.on_queue_declareok, queue=queue_name,exclusive=self.exclusive_queue, auto_delete=self.auto_delete)

    def on_queue_declareok(self, method_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.

        :param pika.frame.Method method_frame: The Queue.DeclareOk frame

        """
        LOGGER.info('Binding %s to %s with %s',
                    self.EXCHANGE, self.QUEUE, self.ROUTING_KEY)
        self._channel.queue_bind(callback=self.on_bindok, queue=self.QUEUE,
                                 exchange=self.EXCHANGE, routing_key=self.ROUTING_KEY)

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.

        """
        #LOGGER.info('Closing the channel')
        self._channel.close()

    def open_channel(self):
        """Open a new channel with RabbitMQ by issuing the Channel.Open RPC
        command. When RabbitMQ responds that the channel is open, the
        on_channel_open callback will be invoked by pika.

        """
        #LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)



class LOPHI_RabbitMQ_Producer(LOPHI_RabbitMQ, multiprocessing.Process):
    """
        This will return a queue that can be used to send messages over RabbitMQ
    """

    def __init__(self, amqp_host,
                 master_queue,
                 queue,
                 exchange_type='direct',
                 routing_key=None,
                 exchange=G.RabbitMQ.EXCHANGE_DIRECT):
        """Create a new instance of the producer class, passing in the AMQP
        host used to connect to RabbitMQ.

        @param Queue master_queue: Queue used to communicate with LOPHI Master process
        @param str amqp_host: The AMQP host to connect to
        @param str queue: RabbitMQ queue to use
        @param str exchange_type: RabbitMQ Exchange type to use (direct, fanout, topic, headers)
        @param str routing_key: RabbitMQ Exchange to use
        @param str exchange: RabbitMQ Exchange to use

        """

        LOGGER.info("* Started RabbitMQ Producer on %s" % queue)

        self.RUNNING = False

        self._master_queue = master_queue

        self.EXCHANGE = exchange
        self.EXCHANGE_TYPE = exchange_type
        self.QUEUE = queue
        
        
        self.exclusive_queue = False
        self.auto_delete = False
        if self.EXCHANGE_TYPE == G.RabbitMQ.TYPE_FANOUT:
            self.exclusive_queue = True
            self.auto_delete = True
        
        if routing_key is None:
            self.ROUTING_KEY = self.QUEUE
        else:
            self.ROUTING_KEY = routing_key

        LOPHI_RabbitMQ.__init__(self, amqp_host)

        multiprocessing.Process.__init__(self)

    def connect(self):
        """
            Overload connect so that we open a publisher connection 
        """

        return pika.BlockingConnection(
                    pika.ConnectionParameters(host=self._host))
#                    self.on_connection_open)

    def open_channel(self):
        """
            Open our channel and delcare our queue
        """
        LOGGER.info('Connection opened')

        # Open our channel
        self._channel = self._connection.channel()
        #print "RabbitMQ Producer: Declaring queue %s exclusive: %s, auto_delete: %s" % (self.QUEUE, self.exclusive_queue, self.auto_delete)
        self._channel.queue_declare(queue=self.QUEUE, exclusive=self.exclusive_queue, auto_delete=self.auto_delete)

    def run(self):
        """
            Run the example consumer by connecting to RabbitMQ and then
            starting the IOLoop to block and allow the SelectConnection to operate.
        """
        # Open connection
        self._connection = self.connect()
        self.open_channel()

        # @todo: FIGURE THIS OUT!
        #print "Declaring exchange %s of type %s" % (self.EXCHANGE, self.EXCHANGE_TYPE)
        self._channel.exchange_declare(exchange=self.EXCHANGE, type=self.EXCHANGE_TYPE)
#        self.setup_exchange(self.EXCHANGE)

        self.RUNNING = True
        # Loop forever relaying the queue to RabbitMQ
        while self.RUNNING:
            # Get our message from the queue
            try:
                message = self._master_queue.get()
            except:
                break
            # Kill self?
            if message == G.CTRL_CMD_KILL:
                LOGGER.debug("Killing RabbitMQ producer.")
                break

            LOGGER.debug("Got message, writing to RabbitMQ...")
            # Publish message
            #print "routing key ", self.ROUTING_KEY
            self._channel.basic_publish(exchange=self.EXCHANGE,
                                        routing_key=self.ROUTING_KEY,
                                        body=message)

#            self._master_queue.task_done()

        logging.debug("RabbitMQ Producer Stopped")
        self.stop()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the producer
        with RabbitMQ.
        """
        LOGGER.info('RabbitMQ Producer Stopping')
#         if self._connection:
#             self._connection.close()

        LOGGER.info('Producer Stopped')

        self.RUNNING = False
        
        try:
            self.terminate()
        except:
            pass

#     def terminate(self):
#         """Overrides multiprocessing.Process's terminate.  Calls self.stop"""
#         self.stop()






class LOPHI_RabbitMQ_Consumer(LOPHI_RabbitMQ, multiprocessing.Process):
    """This is an example consumer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.

    If RabbitMQ closes the connection, it will reopen it. You should
    look at the output, as there are limited reasons why the connection may
    be closed, which usually are tied to permission related issues or
    socket timeouts.

    If the channel is closed, it will indicate a problem with one of the
    commands that were issued and that should surface in the output as well.

    """

    def __init__(self, amqp_host,
                 master_queue,
                 queue,
                 exchange_type='direct',
                 routing_key=None,
                 exchange=G.RabbitMQ.EXCHANGE_DIRECT,
                 auto_delete=False):
        """Create a new instance of the consumer class, passing in the AMQP
        host used to connect to RabbitMQ.

        @param Queue master_queue: Queue used to communicate with LOPHI Master process
        @param str amqp_host: The AMQP host to connect to
        @param str queue: RabbitMQ queue to use
        @param str exchange_type: RabbitMQ Exchange type to use (direct, fanout, topic, headers)
        @param str routing_key: RabbitMQ Exchange to use
        @param str exchange: RabbitMQ Exchange to use

        """
#        self._connection = None
#        self._channel = None
#        self._closing = False
#        self._consumer_tag = None
#        self._host = amqp_host


        LOGGER.debug("Started RabbitMQ Consumer on %s" % queue)

        self._master_queue = master_queue

        self.EXCHANGE = exchange
        self.EXCHANGE_TYPE = exchange_type
        self.QUEUE = queue
        
        self.exclusive_queue = False
        self.auto_delete = auto_delete
        
        if self.EXCHANGE_TYPE == G.RabbitMQ.TYPE_FANOUT:
            self.exclusive_queue = True
            self.auto_delete= True
        
        
        if routing_key is None:
            self.ROUTING_KEY = self.QUEUE
        else:
            self.ROUTING_KEY = routing_key

        LOPHI_RabbitMQ.__init__(self, amqp_host)

        multiprocessing.Process.__init__(self)


#     def open_channel(self):
#         """
#             Open our channel and delcare our queue
#         """
#         LOGGER.info('Connection opened')
# 
#         # Open our channel
#         self._channel = self._connection.channel()
#         self._channel.queue_declare(queue=self.QUEUE)

    
    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer
        for some reason. If RabbitMQ does cancel the consumer,
        on_consumer_cancelled will be invoked by pika.

        """
        #LOGGER.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        #LOGGER.info('Consumer was cancelled remotely, shutting down: %r',
        #            method_frame)
        if self._channel:
            self._channel.close()

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ by sending a
        Basic.Ack RPC method for the delivery tag.

        :param int delivery_tag: The delivery tag from the Basic.Deliver frame

        """
        #LOGGER.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def on_message(self, unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.

        :param pika.channel.Channel unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param str|unicode body: The message body

        """
#         LOGGER.info('Received message # %s from %s: %s',
#                     basic_deliver.delivery_tag, properties.app_id, body)
        self.acknowledge_message(basic_deliver.delivery_tag)

        # Send msg back to LOPHI Master process
        self._master_queue.put(body)

    def on_cancelok(self, unused_frame):
        """This method is invoked by pika when RabbitMQ acknowledges the
        cancellation of a consumer. At this point we will close the connection
        which will automatically close the channel if it's open.

        :param pika.frame.Method unused_frame: The Basic.CancelOk frame

        """
        #LOGGER.info('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()


    def on_bindok(self, unused_frame):
        """Invoked by pika when the Queue.Bind method has completed. At this
        point we will start consuming messages by calling start_consuming
        which will invoke the needed RPC commands to start the process.

        :param pika.frame.Method unused_frame: The Queue.BindOk response frame

        """
        #LOGGER.info('Queue bound')
        self.start_consuming()

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the
        Basic.Cancel RPC command.

        """
        if self._channel:
            #LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def start_consuming(self):
        """This method sets up the consumer by first calling
        add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.

        """
        #LOGGER.info('Issuing consumer related RPC commands')
        # This doesn't seem to be implemented anymore...
#         self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                         self.QUEUE)

    def run(self):
        """Run the example consumer by connecting to RabbitMQ and then
        starting the IOLoop to block and allow the SelectConnection to operate.

        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the consumer
        with RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok
        will be invoked by pika, which will then closing the channel and
        connection. The IOLoop is started again because this method is invoked
        when CTRL-C is pressed raising a KeyboardInterrupt exception. This
        exception stops the IOLoop which needs to be running for pika to
        communicate with RabbitMQ. All of the commands issued prior to starting
        the IOLoop will be buffered but not processed.

        """
        LOGGER.info('Stopping')
        self._closing = True
        self.stop_consuming()
#         self._connection.ioloop.start()
        LOGGER.info('Consumer Stopped')
        
        try:
            self.terminate()
        except:
            pass

#     def terminate(self):
#         """Overrides multiprocessing.Process's terminate.  Calls self.stop"""
#         self.stop()


