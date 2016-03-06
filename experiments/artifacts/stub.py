"""
   Wrapper script for IOZONE on Windows

    (c) 2015 Massachusetts Institute of Technology
"""

import time
import socket
import subprocess

CONNECTION_ATTEMPTS = 20
SLEEP_TIME = 1

def main(args=None):

    import optparse
    opts = optparse.OptionParser()

    opts.add_option("-i", "--ip", action="store", type="string",
                    dest="ip", default="172.20.1.2", help="IP to send output to")

    opts.add_option("-P", "--port", action="store", type="int",
                    dest="port", default=31333, help="Port to send output to")
    
    opts.add_option("-c", "--command", action="store", type="string",
                    dest="command", default=None, help="Command to execute")

    (options, ars) = opts.parse_args(args)

    # Connect to our socket
    connected = False
    for x in range(CONNECTION_ATTEMPTS):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((options.ip,options.port))
            connected = True
            print "* Connected to Analysis machine."
            break
        except:
            print "(%d/%d) Could not connect to analysis host."%(x,CONNECTION_ATTEMPTS)
            print "* Trying again in %d second..."%SLEEP_TIME
            time.sleep(1)
                
    if not connected:
        print "* Exiting without running analysis"
        return
    
        
    # Run our command line program and get response
    print "** Running command: %s"%options.command
    r = ""
    try:
        r = subprocess.check_output(options.command)
    except Exception as e:
        import traceback
        traceback.print_exc()

    # Send response back home and close up
    s.sendall(r)
    s.close()
        

if __name__=="__main__":

    main()

    
