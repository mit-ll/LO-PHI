#!/usr/bin/env python

# Native
import multiprocessing
import sys
import os

# 3rd Party
import pika

# LO-PHI
sys.path.append(os.path.join(os.getcwd(), "../../"))
import lophi.globals as G
from lophi.ext_interface.rabbitmq import LOPHI_RabbitMQ_Producer

amqp_host = "localhost"

input_queue = multiprocessing.Queue()
amqp_producer = LOPHI_RabbitMQ_Producer(amqp_host, input_queue, G.RABBITMQ_SENSOR)
amqp_producer.start()

input_queue.put("howdy")

input_queue.put(G.CTRL_CMD_KILL)

amqp_producer.stop()

#amqp_server.start()
#
#connection = pika.BlockingConnection(pika.ConnectionParameters(
#        host='localhost'))
#channel = connection.channel()
#
#channel.exchange_declare(exchange=G.RABBITMQ_EXCHANGE,
#                         type='direct')
#
#message = ' '.join(sys.argv[1:]) or "info: Hello World!"
#channel.basic_publish(exchange=G.RABBITMQ_EXCHANGE,
#                      routing_key=G.RABBITMQ_SENSOR,
#                      body=message)
#print " [x] Sent %r" % (message,)
#connection.close()
