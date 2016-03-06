"""
    (c) 2015 Massachusetts Institute of Technology
"""

import socket
import sys
 
HOST = 'localhost'
PORT = 31337
 
try:
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error, msg:
  sys.stderr.write("[ERROR] %s\n" % msg[1])
  sys.exit(1)
 
try:
  sock.connect((HOST, PORT))
except socket.error, msg:
  sys.stderr.write("[ERROR] %s\n" % msg[1])
  sys.exit(2)

#data = sock.recv(1500)
#print "out: "+data

cmd = raw_input("INPUT:")
sock.send(cmd)
while 1:
    data = sock.recv(1520)
    print "out: "+data
  

sock.close()
 
sys.exit(0)