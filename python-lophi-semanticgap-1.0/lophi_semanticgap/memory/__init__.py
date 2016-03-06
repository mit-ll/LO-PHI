"""
 This is a super light-weight implementation of Volatility intended for use
 with LO-PHI.  It will connect to the desired System Under Analysis (SUA) using 
 either the network (physical introspection) or a virtual machine.  It will 
 then (ideally) automatically detect the OS of the SUA and set the appropriate
 configurations for introspection of that OS.  At this point, it will sit
 and wait for subscriptions to specific modules.  Once a subscription is made
 it will loop until terminated, requesting and output the appropriate information
 for each subscription.
 
 Author: Chad Spensky (MIT Lincoln Laboratory)
"""

# Native
import sys
import logging
logger = logging.getLogger(__name__)
import multiprocessing
from time import sleep, time

# LO-PHI
import lophi.globals as G
from lophi_semanticgap.memory.volatility_extensions import VolatilityWrapper

# How many seconds to wait between memory polling
ADDR_SPACE_RETRY = 1
# Not exactly sure what this does, but Volatility 1.4rc requires it.
LOPHI_RAM_SIZE = "1G"
LOPHI_TIMEOUT = 100
LOPHI_RETRIES = 5
# Backward compatibility... Convert from int to profile name
OUTPUT_TYPE = "abstract"
OUT_FD = sys.stdout


"""
    If a module is in this list, this means it has been tested, and is ready to 
    rock with our abstract framework!

    WARNING: These were all tested with Xen.  There could be complications when 
    trying to use them with the physical card.
"""
MODULES_DICTIONARY = {
                      "WinXPSP2x86": ['pslist','connections','modules','sockets','getsids'],
                      "WinXPSP3x86": ['pslist','connections','modules','sockets','getsids'],
                      "xpsp0amd64": ['pslist','modules','getsids'],
                      "Win7SP1x64": ['pslist','netscan'],
                      "Win7SP1x86": ['pslist','netscan'],
                      "Win7SP0x86": ['pslist','netscan'],
                      "Win7SP0amd64": ['pslist','netscan'],
                      "LinuxUbuntu_1104_x86": ['linps','linmodules','linux_netstat'],
                      "CentOS5":['linux_task_list_ps']
                      
                      }

"""
    Anything in this list is just verified to work for the given profile.  It 
    may not have render_abstract etc. to work with our framework, and in some 
    cases (eg. apihooks) may continuously render
"""
VERIFIED_MODULES = {
    "WinXPSP2x86": ['apihooks','callbacks','connections','dlldump','dlllist',
                    'files','getsids','handles','kdbgscan','ldrmodules','memmap'
                    ,'moddump','modules','pslist','pstree','regobjkeys',
                    'sockets','ssdt','vaddump','vadinfo','vadtree','vadlist',
                    'window_list'],
    "LinuxUbuntu_1104_x86": ['linps','linmodules','linfiles','linsockets','lindatetime','linux_dmesg','linux_lsmod','linux_netstat','linux_task_list_ps']

}
# These modules seemed to work but had no output... Unsure
#
QUESTIONABLE_MODULES = {
    "WinXPSP2x86": ['driverirp','driverscan','filescan','psxview']
                        
}
# Any module not listed either didn't work, or was not attempted


# This class represents the machine being polled and handles all of the interactions with Volatility
class VolatilityEngine(multiprocessing.Process):
    """
        This class handles bridging the semantic gap using Volatility.
        
        Because of how Volailtity is constructed this will ultimately initalize 
        a new sensor but will use the information from the currently assigned
        sensor.
    """
    lophi_config = None
    volatility_config = None
    init_ok = True
    def __init__(self, machine,
                 plugins,
                 command_queue=None,
                 output_queue=None, 
                 poll_interval=1,
                 debug_vol=False):
        """
            Given a config object, will initialize the SUA thread
        """

        # Init our multiprocess
        multiprocessing.Process.__init__(self)

        
        self.machine = machine
        self.plugins = plugins
        self.poll_interval = poll_interval # seconds
        
        if self.machine.type == G.MACHINE_TYPES.PHYSICAL:
            HOST = "lophi://" + self.machine.memory.sensor_ip
        else:
            HOST = "vmi://" + self.machine.config.vm_name
        
        self.vol = VolatilityWrapper(HOST,
                                     self.machine.config.volatility_profile,
                                     self.machine.memory_get_size())

        self.RUNNING = False
        self.PAUSED = False
        
        self.command_queue = command_queue
        self.output_queue = output_queue


    
    def report_output(self, output):
        """
            This is an abstract function to report output back out control 
            thread.  It also handles logging for this particular SUA
        """
        if self.output_queue is not None:
            self.output_queue.put(output, False)


    def run(self):
        """
            This thread will initialize every module, and then run them forever
            at a fixed interval
        """

        # Make sure that modules were selected
        if len(self.plugins) == 0:
            print "No modules were selected."
            return
        
        self.RUNNING = True
        
        # Loop forever
        while self.RUNNING:

            START = time()
            # Get the command from our controller
            try :
                cmd = self.command_queue.get(False).split(" ")

                logger.debug("Got cmd: %s" % cmd)

                if cmd[0] == "addmodule":
                    logger.debug("Adding module %s" % cmd[1])
                    self.plugins.append(cmd[1])

                if cmd[0] == "delmodule":
                    logger.debug("Removing module %s" % cmd[1])
                    self.plugins.remove(cmd[1])
                    
                if cmd[0] == G.CTRL_CMD_PAUSE:
                    logger.debug("Pausing analysis")
                    self.PAUSED = True
                    
                if cmd[0] == G.CTRL_CMD_UNPAUSE:
                    logger.deubg("Resumming Analysis")
                    self.PAUSED = False
                    
                if cmd[0] == G.CTRL_CMD_KILL or cmd[0] == G.CTRL_CMD_STOP:
                    logger.debug("Got kill command")
                    self.RUNNING = False
                    break
                
            except:
                # Do nothing
                pass

            if self.PAUSED:
                sleep(self.poll_interval)
                continue

            try:

                for plugin_name in self.plugins:
               
                    # Render out output into the format we want
                    output = self.vol.execute_plugin(plugin_name)

#                     logger.debug("Output: %s"%output)

                    # Report the output back to the control process
                    if output is not None:
                        # We have to append our output specific info for processing
                        output['MODULE'] = plugin_name
                        output['SENSOR'] = self.machine.memory.name
                        output['PROFILE'] = self.machine.config.volatility_profile
                        output['MACHINE'] = self.machine.config.name
                        self.report_output(output)
                    else:
                        logger.error("No data processer exists for %s."%plugin_name)

            except:
                logger.error("There was a problem executing modules. Trying to reload address space... (Is the VM Running?)")            
                raise
    

            # Wait for X seconds until we poll again
            elapsed_time = time() - START
            if elapsed_time < self.poll_interval:
                sleep(self.poll_interval - elapsed_time)


        logger.debug("Stopping memory analysis")
        # Kill process
        sys.exit(0)