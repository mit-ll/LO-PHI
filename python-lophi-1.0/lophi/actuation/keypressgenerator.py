#!/usr/bin/env python

""""
 LOPHI Actuation Library

@TODO: add mouse support

    Script syntax:
        SPECIAL: <LEFT_GUI> n
        TEXT: wget ftp://get_test_malware_here
        MOUSE: (TODO)
        SLEEP: (Time in seconds)
    
    Each line is a command message
    Header is necessary to differentiate text versus special keys

    (c) 2015 Massachusetts Institute of Technology
"""

# Native Libraries
import io
import re
import socket
import logging
import os
import string

# LO-PHI
import lophi.globals as G
import lophi.actuation.keycodes as keycodes


class KeypressGenerator(object):
    """
        This object takes care of generating input used for actuating physical 
        and virtual machines using the keyboard and mouse
    """


    class REPLACE_STRINGS:
        """ Strings to replace in our scripts """
        ip = "%%IP%%"
        port = "%%PORT%%"
        username = "%%USERNAME%%"
        password = "%%PASSWORD%%"
        dir = "%%DIR%%"
        #exe = "%%EXE%%"
    
    # comment regexp
    comment_pattern = re.compile('^#..*$')
    # cmd regexp
    cmd_pattern = re.compile('^(\w+):(..*)$')

    def __init__(self):
        if self.__class__ == KeypressGenerator:
            raise("Abstract class initialized directly!")

    def get_ftp_script(self, profile, ftp_info, hit_enter=True):
        """
            Return a script for the actuation sensor that will run the contents in
            the given directory on a system of the given profile
            
            @param profile: Profile of the system that we are running code on
            @param ftp_info: (ip, user, password, directory)
            @return: list of actions that can be sent to control sensor
        """
        # Get our FTP info to fill in
        FTP_IP = ftp_info['ip']
        FTP_PORT = ftp_info['port']
        FTP_USER = ftp_info['user']
        FTP_PASSWORD = ftp_info['pass']
        FTP_DIR = ftp_info['dir']
        #FTP_EXE = ftp_info['exe']
    
        # Get the appropriate script
        script = None
    
        """
            Windows
        """
        if profile in G.PROFILE_TO_SCRIPT:
            script = os.path.join(G.DIR_ROOT, G.DIR_ACTUATION_SCRIPTS, G.PROFILE_TO_SCRIPT[profile])
    
        if script is None:
            logging.error("No ftp execution script exists for %s"%profile)
            return None
        
        else:
            if not os.path.exists(script):
                logging.error("File (%s) does not exist!" % script)
                return None
    
            # open file
            f = open(script, 'r')
            SCRIPT = f.read()
            f.close()
    
            SCRIPT = SCRIPT.replace(self.REPLACE_STRINGS.ip, FTP_IP)
            SCRIPT = SCRIPT.replace(self.REPLACE_STRINGS.port, str(FTP_PORT))
            SCRIPT = SCRIPT.replace(self.REPLACE_STRINGS.username, FTP_USER)
            SCRIPT = SCRIPT.replace(self.REPLACE_STRINGS.password, FTP_PASSWORD)
            SCRIPT = SCRIPT.replace(self.REPLACE_STRINGS.dir, FTP_DIR)
            #SCRIPT = SCRIPT.replace(self.REPLACE_STRINGS.exe, FTP_EXE)
            
            script = self.text_to_script(SCRIPT)
            
            if hit_enter:
                script.append(self.parse_special("RETURN"))
            
            return script
                


    def text_to_script(self, script):
        """
            Parses specified file into a list of messages easily digested by 
            python.
            
            @param filename: Filename of the script to be converted to python 
                             object.
        """
        # list to return
        msg_list = list()

        # Split on newliens
        script = script.split("\n")

        # parse the script line by line
        for line in script:
            # Parse our line
            msg = self.parse_line(line)

            if msg is not None:
                msg_list.append(msg)
                logging.debug(msg)

        return msg_list


    def parse_line(self, line):
        """
            Parses line into a msg
            
            parse commands are overloaded by subclasses
            
            @param line: Line from script file
            @return: Formatted output to sent to SUT
        """
        # Ignore comments and empty lines
        if (line == '\n') or self.comment_pattern.match(line) or (line == ''):
            return None

        # Not a comment, try to match command
        cmd_match = self.cmd_pattern.match(line)
        if cmd_match:

            # Determine type of command
            groups = cmd_match.groups()
            cmd = groups[0]
            payload = groups[1].lstrip()

            # How should we treat this line?
            if cmd == 'SPECIAL':
                return self.parse_special(payload)
            elif cmd == 'TEXT':
                return self.parse_text(payload)
            elif cmd == 'MOUSE':
                return self.parse_mouse(payload)
            elif cmd == 'SLEEP':
                return self.parse_sleep(payload)
            else:
                # Not recognized, raise an Error
                raise Exception("Could not parse line '%s'" % line)

        # Not recognized, raise an Error
        raise Exception("Could not parse line '%s'" % line)


    """
        Abstract functions
    """
    def parse_special(self):
        """
            Returns message containing special key presses based on the payload.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")


    def parse_text(self):
        """
            Returns message containing text to type via keyboard emulation.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")


    def parse_mouse(self, payload):
        """
            Returns message containing mouse comands.
        """
        raise NotImplementedError("ERROR: Unimplemented function.")



    

class KeypressGeneratorPhysical(KeypressGenerator):
    """
        This object takes care of generating input used for actuating physical 
        and virtual machines using the keyboard and mouse
    """
    
    def _create_msg(self, cmd_type, payload):
        """
            Format command for arduino
            
            @param cmd_type: Type of command
            @param payload: Payload to send
            @return: Text to be sent over the network
        """
        return cmd_type + ':' + payload
    
    def parse_special(self, payload):
        """
            Returns message containing special key presses based on the payload.
            
            @param payload: Input from script, delimited by spaces
            @return: Appropriate input for Physical machines
        """
        # strip newline
        key_list = payload.rstrip().split()

        p = list()

        # convert special characters into Arduino codes
        for key in key_list:
            # Special Key?
            if key in keycodes.ARDUINO_KEYMAP:
                hex_key = keycodes.ARDUINO_KEYMAP[key][0][2:]
            # Normal Key?
            else:
                hex_key = hex(ord(key))[2:]
                
            # Arduino expects 5 bytes for each keypress
            hex_key += ' '*(5-len(hex_key))
            p.append(hex_key)
            
        # Join the list
        p = ''.join(p)

        return self._create_msg(G.SENSOR_CONTROL.KEY_SP_CMD, p)


    def parse_text(self, payload):
        """
            Returns message containing text to type via keyboard emulation on Arduino.
            
            @param payload: Input from script, delimited by spaces
            @return: Appropriate input for Physical or Virtual Machine 
        """
        return self._create_msg(G.SENSOR_CONTROL.KEYB_CMD, payload)


    def parse_sleep(self, payload):
        """
            Returns message containing a time to sleep
            
            @param payload: Input from script, delimited by spaces
            @return: Appropriate input for Physical or Virtual Machine 
        """
        return self._create_msg(G.SENSOR_CONTROL.KEY_SLEEP, payload)


    def parse_mouse(self, payload):
        """
            Returns message containing mouse comands.
            
            @todo: IMPLEMENT MOUSE FUNCTIONS
        """
        logging.error("Mouse Commands are not implemented yet.")
        return None
    
    
    
    
class KeypressGeneratorVirtual(KeypressGenerator):
    """
        This object takes care of generating input used for actuating physical 
        and virtual machines using the keyboard and mouse
    """
    
    
    def parse_special(self, payload):
        """
            Returns message containing special key presses based on the payload.
            
            @param payload: Input from script, delimited by spaces
            @return: Appropriate input for Physical or Virtual Machine 
        """
        # strip newline
        key_list = payload.rstrip().split()

        p = list()

        for key in key_list:
            # Everything is indexed by upper case
            key = string.upper(key)
            # Do we have a keycode for this?
            if key in keycodes.KEYCODES:
                p.append(keycodes.KEYCODES[key])
            else:
                logging.error("Could not find %s in our keycodes" % key)

        return [G.SENSOR_CONTROL.KEY_SP_CMD, p]


    def parse_text(self, payload):
        """
            Returns message containing text to type via keyboard emulation on Arduino.
            
            @param payload: Input from script, delimited by spaces
            @return: Appropriate input for Physical or Virtual Machine 
        """
        return [G.SENSOR_CONTROL.KEYB_CMD, keycodes.get_codes(payload)]


    def parse_sleep(self, payload):
        """
            Returns message containing time to sleep
            
            @param payload: Input from script, delimited by spaces
            @return: Appropriate input for Physical or Virtual Machine 
        """
        return [G.SENSOR_CONTROL.KEY_SLEEP, payload]


    def parse_mouse(self, payload):
        """
            Returns message containing mouse comands.
            
            @todo: IMPLEMENT MOUSE FUNCTIONS
        """
        logging.error("Mouse Commands are not implemented yet.")
        return None

