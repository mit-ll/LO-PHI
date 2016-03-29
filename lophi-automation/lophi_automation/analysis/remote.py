"""
    A class for running analysis programs on a SUT and getting the output

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import logging
logger = logging.getLogger(__name__)
import os
import shutil
import socket
import time

# LO-PHI
import lophi.globals as G

STUB_FILE = "stub.py"

class RemoteAnalysis:

    def __init__(self,profile,
                 control_sensor,
                 ftp_info,
                 ftp_directory=G.FTP_ROOT):
        """
            Initalize our remote analysis

            @param profile: Profile of machine to run analysis on
            @param control_sensor: Control sensor for SUT
            @param ftp_info: (ip, user,pass [,directory]) of our local ftp server
            @param ftp_directory: Local ftp directory to copy contents to
        """

        self.profile = profile
        self.control_sensor = control_sensor
        self.ftp_info = ftp_info
        self.ftp_directory = ftp_directory

    def run_analysis(self, remote_command,
                     execution_directory=None,
                     init_commands=None,
                     bind_ip="0.0.0.0"):
        """

            @param execution_directory: Directory with executables
            @param remote_command: Command to execute on SUT
            @param init_commands: Initialization commands that will be run on
            the command line before the analysis commands

            @return: Results from the SUT of executing the given command
        """

        # First, find a directory to temporarily store our files
        if not os.path.exists(self.ftp_directory):
            logger.error("FTP directory %s does not exist!"%self.ftp_directory)
            return None

        # Does the directory we are trying to ftp over exist?
        if execution_directory is not None and not os.path.exists(execution_directory):
            logger.error("Execution directory %s does not exist!"%execution_directory)
            return None

        # Find a temporary directory name
        idx = 0
        tmp_dir = "tmp"+str(idx)
        while os.path.exists(os.path.join(self.ftp_directory,tmp_dir)):
            idx += 1
            tmp_dir = "tmp"+str(idx)

        # Update our ftp_info
        tmp_dir_local = os.path.join(self.ftp_directory,tmp_dir)
        self.ftp_info['dir'] = tmp_dir

        # Copy the contents over to our ftp
        if execution_directory is not None:
            try:
                shutil.copytree(execution_directory, tmp_dir_local)
            except:
                logger.error("Could not copy %s to %s"%(execution_directory,tmp_dir_local))
                return None
        else:
            try:
                os.makedirs(tmp_dir_local)
            except:
                logger.error("Could not create temp directory: %s"%tmp_dir)
                return None

        # Get our FTP script to actuate the machine
        keypress_generator = self.control_sensor.keypress_get_generator()
        ftp_script = keypress_generator.get_ftp_script(self.profile,
                                                       self.ftp_info)

        # Try copying our stub
        try:
            shutil.copy(STUB_FILE, tmp_dir_local)
        except:
            logger.error("Could not copy our python stub file '%s' to '%s'."%(
                                                                STUB_FILE,
                                                                tmp_dir_local))
            return None

        # Create our lophi.bat
        f = open(os.path.join(tmp_dir_local,"lophi.bat"),"w+")
        f.write("set LOPHI=%CD%\n")
        if init_commands is not None:
            for c in init_commands:
                f.write(c+"\n")
        f.write("python \"%%LOPHI%%\\stub.py\" -i %s -c \"%s\"\n"%(self.ftp_info['ip'],
                                                                   remote_command))
        f.write("exit")
        f.close()

        # Actuate the SUT to download and execute lophi.bat
        self.control_sensor.keypress_send(ftp_script)

        command_script = keypress_generator.parse_text("python stub.py")

        # At this point the SUT should be trying to connect to us..

        logger.info("Opening socket and waiting for callback...")

        # Open our socket to listen for our callback
        while 1:
            try:
                sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                sock.bind((bind_ip,G.SUT_ANALYSIS_PORT))
                sock.listen(0)
                break
            except:
                logger.info("Socket in use on port %d, trying again..."%G.SUT_ANALYSIS_PORT)
                time.sleep(1)

        # Temporarily set timeout and wait for our callback connection
        sock.settimeout(60)
        try:
            conn, addr = sock.accept()
            logger.info("Got connection from %s."%str(addr))
        except:
            logger.error("SUT never connected to callback.  (Timeout)")
            return
        sock.settimeout(None)
        sock.setblocking(True)

        logger.info("Got connection, waiting for response from command (%s)..."%remote_command)

        return_value = ""
        while True:
#             try:
                data = conn.recv(1024)
                if len(data) == 0:
                    break
                else:
                    return_value += data
#             except:
#                 break

        logger.info("Done executing command. Returning results. (%d bytes)"%len(return_value))

        sock.close()

        # Clean up our temp files
        try:
            shutil.rmtree(tmp_dir_local)
        except:
            logger.error("Could not delete tmp directory. (%s)"%tmp_dir_local)


        return return_value