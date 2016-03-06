"""
    This super lightweight server is meant to be run on the system under 
    analysis (i.e. the system with the LO-PHI card in it).  It simply listens
    on a TCP socket for commands to generate files of a given size, filled
    with a given pattern.
"""

import socket     
import time
import os
 
# Let's set up some constants
HOST = ''
PORT = 31337  
BUFSIZE = 4096

# Open our socket
serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
##bind our socket to the address
serv.bind((HOST,PORT))
serv.listen(5)
while 1:
    print "Waiting for client on port %d..."%(PORT)
    (conn,addr) = serv.accept()

    # Get our data
    data = conn.recv(BUFSIZE)
    print data
    params = data.split(" ")
    pattern = params[0]     # 4-byte pattern
    count = int(params[1])       # Patterns per file
    files = int(params[2])       # Number of files to create
    sleep = float(params[3])       # Sleep time between files
    directory = params[4]
          
    # Create the proper number of files
    for i in range(files):
        # Set our current filename and write to disk
        try:
            newfile = os.path.join(directory, "FILE" + str(i))
            print "Creating %s with size %d bytes" % (newfile, len(pattern) * count)
            f = open(newfile, 'w+')
            f.write(str(pattern) * int(count))
            f.close()
            time.sleep(sleep)
        except:
            print "ERROR writing file!  Restarting server..."
            raise
    
    conn.close()

    print "Cleaning up files..."
    # Clean up all of the files
    for i in range(files):
        # Set our current filename and remove from disk
        try:
            newfile = os.path.join(directory, "FILE" + str(i))
            os.remove(newfile)
        except:
            print "ERROR deleting file!  Restarting server..."
            raise
        

    
serv.close()
    
        
