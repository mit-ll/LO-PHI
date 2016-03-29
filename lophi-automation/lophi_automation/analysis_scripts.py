"""
    Base class for all analysis scripts

    (c) 2015 Massachusetts Institute of Technology
"""
import multiprocessing
import time
import os
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G

# LO-PHI Automation
from lophi_automation.database.db import DatastoreAnalysis


class LophiAnalysis(multiprocessing.Process):
    
    analysis_id = 0
    
    def __init__(self, command_queue,
                 lophi_command=None, 
                 services_host=G.RabbitMQ.AMQP_HOST,
                 machine=None,
                 machine_queue=None,
                 machine_name=None,
                 running_dict=None,
                 lophi_analysis_id=None,
                 machine_list=None):
        """ 
            Setup our globals/queues etc. 
        """
        # Save our machine
        self.machine = machine
        self.machine_queue = machine_queue
        self.machine_name = machine_name
       
        # Setup a queue to receive commands on
        self.command_queue = command_queue
        
        # Save any passed arguments (e.g. ftp info)
        self.lophi_command = lophi_command
        
        # Save our services hostname (amqp, mongodb)
        if lophi_command is not None and \
           "services_host" in lophi_command.__dict__:
            self.services_host = lophi_command.services_host
        else:
            self.services_host = services_host

        # All analysis should get an ID
        self.id = self.analysis_id
        self.analysis_id += 1
        
        # Shared dictionary to keep track of running analysis
        self.running_dict = running_dict
        # Key track of the analysis id for queued/running status
        self.lophi_analysis_id = lophi_analysis_id
        
        self.machine_list = machine_list
        
        # Should we continue running after the user-defined analysis?
        self.CONTINUE_EXECUTION = True
        
        if "NAME" not in self.__dict__:
            self.NAME = self.__class__.__name__
        
        # Init our multiprocess
        multiprocessing.Process.__init__(self)

    def analysis_start(self):
        """
            Commands to execute when starting analysis.  Once this returns the
            analysis will wait for commands from the user.
            
            NOTE: The threads will continue execute until a stop command is
                    received
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
            
    def analysis_pause(self, args):
        """
            Commands to execute when pausing analysis
        """
        raise NotImplementedError("ERROR: Unimplemented function.")    

    def analysis_resume(self, args):
        """
            Commands to execute when resuming analysis
        """
        raise NotImplementedError("ERROR: Unimplemented function.")    

    def analysis_stop(self, args):
        """
            Commands to execute when stopping analysis
        """
        raise NotImplementedError("ERROR: Unimplemented function.")
        
    def _start_analysis(self):
        """
            Start the requested analysis.
        """
        
    def run(self):
        """" 
            Run analysis and then continuously read and process commands from 
            our command queue.    
        """
        
        logger.info("Started LO-PHI analysis '%s'. (PID: %d)"%(self.NAME,
                                                               os.getpid()))
        
        COMMANDS = {
            #  Command                      Function
            G.CTRL_CMD_PAUSE        :   self.analysis_pause,
            G.CTRL_CMD_UNPAUSE      :   self.analysis_resume,
            G.CTRL_CMD_STOP         :   self.analysis_stop
            }
        
        # grab a machine from the queue if one wasn't explicity set
        if self.machine_name is not None:
            self.machine = self.machine_list[self.machine_name]
            
        if self.machine is None:
            logger.error("No machine provided to analysis.")
            return False
        
        self.machine.ALLOCATED = self.id
                
        # Start our analysis
        logger.debug("Acquiring mutex and starting analysis...")
        with self.machine.MUTEX:
            
            # Put ourselves in the running pool
            if self.running_dict is not None and \
               self.lophi_analysis_id is not None:
                # Moved from queued to running
                self.running_dict['queued'].remove(self.lophi_analysis_id)
                self.running_dict['running'].append(self.lophi_analysis_id)
            
            if self.lophi_command is not None and \
               self.lophi_command.db_analysis_id is not None:
                try:
                    DB_analysis = DatastoreAnalysis(self.services_host)
                    DB_analysis.update_analysis_machine(
                        self.lophi_command.db_analysis_id, self.machine)
                    DB_analysis.update_analysis(
                        self.lophi_command.db_analysis_id,
                        "status",
                        G.JOB_RUNNING)
                    DB_analysis.update_analysis(
                        self.lophi_command.db_analysis_id,
                        "started",
                        time.time())
                except:
                    logger.error("Could not update the database with analysis info.")
                
            # Run the user-defined analysis
            try:
                # Set our machine to the proper profile
                if self.lophi_command is not None:
                    logger.debug("Setting machine profile...")
                    if self.lophi_command.volatility_profile is not None:
                        prof_status = self.machine.set_volatility_profile(
                            self.lophi_command.volatility_profile)
                    elif self.VOLATILITY_PROFILE is not None:
                        prof_status = self.machine.set_volatility_profile(
                            self.VOLATILITY_PROFILE)
                    if not prof_status:
                        err = "Could not set profile (%s) for machine (%s)."%(
                                        self.machine.config.volatility_profile,
                                        self.machine.config.name)
                        logger.error(err)

                #
                #    Run the actual analysis
                #
                self.analysis_start()
                
                if self.lophi_command is not None and \
                   self.lophi_command.db_analysis_id is not None:
                    try:
                        DB_analysis.update_analysis(
                            self.lophi_command.db_analysis_id,
                            "status",
                            G.JOB_DONE)
                    except:
                        logger.warn("Could not update the database with analysis info.")

            except:
                logger.error("Analysis failed to start!")
                
                G.print_traceback()
                
                if self.lophi_command is not None and \
                   self.lophi_command.db_analysis_id is not None:
                    try:
                        DB_analysis.update_analysis(
                            self.lophi_command.db_analysis_id,
                            "error",
                            G.get_traceback())
                        DB_analysis.update_analysis(
                            self.lophi_command.db_analysis_id,
                            "status",
                            G.JOB_FAILED)
                    except:
                        logger.warn("Could not update the database with analysis info.")
                
                self.CONTINUE_EXECUTION = False
                # Try to stop anything that may have started.
                try:
                    self.analysis_stop()
                except:
                    pass

            # Wait for output to start returning, and handle appropriately
            while False and self.CONTINUE_EXECUTION:
                
                logger.debug("Waiting for cmd")
                
                command = self.command_queue.get()
                
                logger.debug("Got: %s" % command)
                
                # Split up our command
                cmd = command.rstrip().split(" ")

                # See if it's valid command
                if cmd[0] not in COMMANDS.keys():
                    logger.error("Got invalid command: %s" % command)
                else:
                    logger.debug("Executing %s"%cmd[0])
                    try:
                        COMMANDS[cmd[0]](command)
                    except:
                        G.print_traceback()
                    
                    if cmd[0] == G.CTRL_CMD_STOP or cmd[0] == G.CTRL_CMD_KILL:
                        break
                    
        # Mark analysis completion time
        try:
            DB_analysis.update_analysis(self.lophi_command.db_analysis_id, 
                                    "completed",
                                    time.time())
        except:
            logger.warn("Could not update the database with analysis info.")

        # Clean up and release machine
        logger.debug("Release machine back to queue.")
        self.machine.ALLOCATED = -1
        
        # remove from running analysis
        if self.running_dict is not None and self.lophi_analysis_id is not None:
            self.running_dict['running'].remove(self.lophi_analysis_id)
        
        # Did we get our machine from the queue? Put it back.
        if self.machine_queue is not None and self.machine_name is not None:
            self.machine_queue.put(self.machine_name)

        self.command_queue.close()
        logger.debug("LophiAnalysis stopped.")
        return True
        
    def get_name(self):
        if "NAME" in self.__dict__:
            return self.NAME
        else:
            return self.__class_.__name__
        
    def get_machine_type(self):
        if "MACHINE_TYPE" in self.__dict__:
            return self.MACHINE_TYPE
        else:
            return None
        
    def get_volatility_profile(self):
        if "VOLATILITY_PROFILE" in self.__dict__:
            return self.VOLATILITY_PROFILE
        else:
            return None
        
    def get_description(self):
        if "DESCRIPTION" in self.__dict__:
            return self.DESCRIPTION
        else:
            return "No Description Provided."
        
    def __str__(self):
        """
            Nicely print our analysis
        """ 
        
        o = "[%s] Machine Type: %d, Volatility Profile: %s" % (
            self.get_name(),
            self.get_machine_type(),
            self.get_volatility_profile())
        o += " "*len(self.get_name())+"  %s" % self.get_description()
        
        return o
