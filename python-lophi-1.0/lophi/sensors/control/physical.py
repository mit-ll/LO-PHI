"""
    Class for controlling physical machines

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import socket
import logging
logger = logging.getLogger(__name__)
import time

import lophi.globals as G
from lophi.sensors.control import ControlSensor
from lophi.actuation.keypressgenerator import KeypressGeneratorPhysical

class ControlSensorPhysical(ControlSensor):
    
    SOCK_TIMEOUT = 60
    RETRIES = 3
    
    def __init__(self, sensor_ip, sensor_port=G.SENSOR_CONTROL.DEFAULT_PORT,name=None):
        """
            Initialize our control sensor (e.g arduino)
        """
        self.sensor_ip = sensor_ip
        self.sensor_port = sensor_port
        self._sock = None
        
        if name is not None:
            self.name = name
        
#         self.sensor_reset()
        
        self._connect()
        
        ControlSensor.__init__(self)
        
    def __del__(self):
        """ Try to clean up our socket """
        try:
            logger.debug("Disconnecting physical control sensor.")
            self._disconnect()
        except:
            pass

    def _connect(self):
        """
            Connect to the arduino server
        """
        if self._sock is None:
            logger.debug("Connecting to control sensor. (%s:%d)"%(self.sensor_ip,
                                                                  self.sensor_port))
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.connect((self.sensor_ip, self.sensor_port))
                # Set timeout
                self._sock.settimeout(self.SOCK_TIMEOUT)
                return True
            except:
                logger.error("Could not connect to control sensor at %s:%s"%
                              (self.sensor_ip,self.sensor_port))
                
                return False
        else:
            return True

    def _disconnect(self):
        """
            Disconnect from the arduino server
        """
        try:
            # Send end of transmission
            self._sock.sendall(G.SENSOR_CONTROL.END_TRANSMISSION)
        except:
            pass
        
        try:
            # Close socket
            self._sock.close()
        except:
            pass
        
        self._sock = None
        
    def _read_response(self):
        """
            Read response from the arduino
        """
        try:
            data = self._sock.recv(1024)
        except:
            return None
        
        if len(data) == 0: 
            return None
        else:
            return data
        
    def _send_comand(self,msg):
        """
            Send a message to the arduino with end flag
        """
        for attempt in range(self.RETRIES):
            if not self._connect():
                return False
            
            try:
                self._sock.sendall(msg)
                self._sock.sendall(G.SENSOR_CONTROL.END_MSG)

                response = self._read_response()

                if response is None:
                    logger.warn("Couldn't send command to the control "
                                "sensor (%d/%d)."%(attempt+1,self.RETRIES))
                    self._disconnect()
                    continue

                elif response == G.SENSOR_CONTROL.RESPONSE_DONE:
                    return True
                else:
                    return response
            except:
                logger.warn("Couldn't send command to the control sensor ("
                            "%d/%d)."%(attempt+1, self.RETRIES))
                self._disconnect()
                pass
        
        return False
        
    def sensor_reset(self):
        """
            Reset the Arduino
        """
        return self._send_comand(G.SENSOR_CONTROL.RESTART_CMD)

    def mouse_click(self,x,y,button=None,double_click=False):
        """
            This will move the mouse the specified (X,Y) coordinate and click
        """
        if not self._connect():
            return False

        return self._send_comand(G.SENSOR_CONTROL.MOUSE_CMD+":"+"%5s"%x+"%5s"%y)
        
    def mouse_wiggle(self, enabled=True):
        """
            Toggle whether we move the mouse
        """
        
        return self._send_comand(G.SENSOR_CONTROL.MOUSE_WIGGLE+":"
                                 + str(int(enabled)))

    def keypress_send(self, keypresses):
        """
           Given a list of keypress instructions will emulate them on the SUT.
            
            @param keypresses: list of commands to send to keyboard emulator
        """
        
        if not self._connect():
            return False
        
        # send messages
        for msg in keypresses:
            logger.info("Sending keypress: %s" % msg)
        
            self._send_comand(msg)
        
            time.sleep(G.SENSOR_CONTROL.SLEEP_INTER_CMD)

    def keypress_get_generator(self):
        """
            Return a generator to convert scripts into a language this sensor 
            understands
            
            @return: KeypressGenerator for virtual machines
        """
        
        return KeypressGeneratorPhysical()

    def power_on(self):
        """ Turn power on """
        
        if not self._connect():
            return False
        
        if self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.ON:
            return self._send_comand(G.SENSOR_CONTROL.ON_CMD)
        else:
            return True

    def power_off(self):
        """ Turn power off """
        
        if not self._connect():
            return False
        
        if self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.OFF:
            return self._send_comand(G.SENSOR_CONTROL.OFF_CMD)
        else:
            return True

    def power_shutdown(self):
        """ Shutdown nicely """
        
        if not self._connect():
            return False
        
        return self._send_comand(G.SENSOR_CONTROL.SHUTDOWN_CMD)

    def power_status(self):
        """ Get power status of machine """
        
        if not self._connect():
            return False
        
        # Get response from sensor
        resp = self._send_comand(G.SENSOR_CONTROL.STATUS_CMD)
        return resp

    def power_reboot(self):
        """ Reboot the machine """
        
        timeout = 60
        start = time.time()
        # Do we need to shutdown that machine?
        if self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.OFF:
            self.power_shutdown()
        
        # Wait for the OS to shutdown gracefully
        while self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.OFF:
            # If it's taking too long, just kill the power
            if time.time() - start > timeout:
                self.power_off()
            time.sleep(.5)
        
        # Let the power cycle for a bit.
        time.sleep(.5)
        
        # Power the machine back on.
        self.power_on()

    def power_reset(self):
        """ Reset power """

        # Do we need to shutdown that machine?
        if self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.OFF:
            self.power_off()
        
        # Wait for the power to go off
        while self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.OFF:
            time.sleep(.5)
        
        # Let all the power cycle out
        time.sleep(10)
        
        # Power the machine back on.
        self.power_on()
        
        # Wait for the machine power up
        while self.power_status() != G.SENSOR_CONTROL.POWER_STATUS.ON:
            time.sleep(.5)
            
        return True