"""
    This is just a very simple FTP Server used to serve executables to our
    machines

    (c) 2015 Massachusetts Institute of Technology
"""

# TODO: The pyftpdlib package needs to be updated!

import os
import logging
logger = logging.getLogger(__name__)

# 3rd Party
from pyftpdlib import ftpserver
from pyftpdlib.ftpserver import FTPHandler

# LO-PHI
import lophi.globals as G
# LO-PHI Automation
from lophi_automation.database.db import DatastoreSamples


class LoPhiFtpServer():

    def __init__(self, homedir, user=G.FTP_USER, password=G.FTP_PASSWORD,
                 port=G.FTP_PORT,
                 db_host=G.DB_HOST):
        """
            Initialize FTP settings
        """
        
        logger.debug("* Starting Incoming FTP Server")

        self.user = user
        self.password = password

        # Instantiate a dummy authorizer for managing 'virtual' users
        authorizer = ftpserver.DummyAuthorizer()

        # Ensure our root directory exists
        if not os.path.exists(homedir):
            os.makedirs(homedir)
        
        # create upload directory if it doesn't exist
        if not os.path.exists(os.path.join(homedir,'upload')):
            os.makedirs(os.path.join(homedir,'upload'))

        # Define a new user having full r/w permissions and a read-only
        # anonymous user
        authorizer.add_user(user, password=password, homedir=homedir, perm='elradfmw')

        # Instantiate FTP handler class
        handler = JobHandler
        handler.authorizer = authorizer
        
        # TODO: check if this works
        # create connection to our db
        handler.datastore = DatastoreSamples(db_host)

        # Define a customized banner (string returned when client connects)
        handler.banner = "LO-PHI FTP Server at your service!"

        # Instantiate FTP server class and listen to 0.0.0.0:21
        address = ('', port)
        self.server = ftpserver.FTPServer(address, handler)

        # set a limit for connections
        self.server.max_cons = 256
        self.server.max_cons_per_ip = 5

    def run(self):
        """
            Run the actual server
        """
        # start ftp server
        self.server.serve_forever()

class JobHandler(FTPHandler):

    def on_connect(self):
        logger.debug("%s:%s connected" % (self.remote_ip, self.remote_port))

    def on_disconnect(self):
        # do something when client disconnects
        pass

    def on_login(self, username):
        # do something when user login
        pass

    def on_logout(self, username):
        # do something when user logs out
        pass

    def on_file_sent(self, f):
        # do something when a file has been sent
        pass

    def on_file_received(self, filepath):
        # do something when a file has been received
        logger.info("Received sample: %s"%filepath)
        
        # upload sample to our db
        self.datastore.upload_sample(filepath)
        
        # delete the uploaded sample
        if "/upload/" in filepath:
            os.remove(filepath)

    def on_incomplete_file_sent(self, f):
        # do something when a file is partially sent
        pass

    def on_incomplete_file_received(self, f):
        # remove partially uploaded files
        os.remove(file)