"""
    This connects to multiple controllers running across numerous physical
    servers to control large scale experiments.

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import multiprocessing
import random
import logging

logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G
# LO-PHI Automation
import lophi_automation.configs.helper as Configs
import lophi_automation.ext_interface.rabbitmq as rabbitmq
import lophi_automation.database.db as DB
from lophi_automation.network.command import LophiCommand

CMD_PREFIX = G.bcolors.HEADER + "lophi-controller$ " + G.bcolors.ENDC
LISTS = {'machines',
         'controllers',
         'analysis'}


class LoPhiMaster:
    """
        This class will connect to all of our controllers and relay messages
        amongst them.  Potentially will have load-balancing etc. in the future.
    """

    def __init__(self, options, positionals):
        """
            Initialize our master with the config of controllers
        """

        print "* Starting up LOPHI Master Process"

        self.COMMANDS = {G.CTRL_CMD_START: self.command_start,
                         G.CTRL_CMD_LIST: self.command_list,
                         G.CTRL_CMD_PAUSE: self.command_abstract,
                         G.CTRL_CMD_UNPAUSE: self.command_abstract,
                         G.CTRL_CMD_SPLASH: self.command_splash,
                         G.CTRL_CMD_UPDATE_HW: self.command_update_hw,
                         G.CTRL_CMD_STOP: self.command_abstract,
                         G.CTRL_CMD_DIE: self.command_abstract,
                         G.CTRL_CMD_ATTACH: self.command_abstract,
                         G.CTRL_CMD_EXECUTE: self.command_abstract}

        self.MSG_TYPES = set([G.CTRL_TYPE, G.REG_TYPE])

        # response header
        self.RESP_HEADER = "[LOPHI Master] "

        logger.debug("Importing config files...")

        # Save our config file
        self.master_config_file = options.config_file

        # Save our config file
        self.analysis_directory = options.analysis_directory

        # Read our config into an internal structure           
        self.config_list = Configs.import_from_config(self.master_config_file,
                                                      "controller")

        # Read our analysis scripts into an internal structure
        self.update_analysis()

        # Connect to our database
        self.DB_analysis = DB.DatastoreAnalysis(options.services_host)

        # Set our RabbitMQ host
        self.amqp_host = options.services_host

    def update_analysis(self):
        """
            Read our directory and updated our list of found analysis to reflect
            the current state of the file system
        """
        # Read our analysis scripts into an internal structure
        self.analysis_list = Configs.import_analysis_scripts(
            self.analysis_directory)

    def command_list(self, command):
        """
            Generic command to list statuses of the server
        """

        # See if the list exists and return results
        if len(command.args) > 0 and command.args[0] in LISTS:
            resp = []


            # Print out our available machines
            if command.args[0] == "machines":
                # Loop over controllers
                for c in self.config_list:

                    # Get updated list of machiens
                    self.config_list[c].get_machines()

                    # Print output
                    machines_tmp = self.config_list[c].machines

                    resp.append("--- %s" % c)
                    for x in machines_tmp:
                        name = machines_tmp[x].config.name
                        m_type = machines_tmp[x].type
                        profile = machines_tmp[x].config.volatility_profile
                        resp.append(" [%s] Type: %s, Profile: %s" % (
                        name, m_type, profile))
                    resp.append("--- %s" % c)

            # Print out our LO-PHI configs
            if command.args[0] == "controllers":

                if len(self.config_list) == 0:
                    resp.append("No controllers are configured.")
                else:
                    resp.append("--- Available Controllers")
                    for x in self.config_list:
                        resp.append(str(self.config_list[x]))
                    resp.append("--- Available Controllers")

            # Print out our running analyses
            if command.args[0] == "analysis":

                # Ensure our list
                self.update_analysis()

                # Loop over controllers
                for c in self.analysis_list:
                    analysis, filename = self.analysis_list[c]

                    resp.append("\n[%s] %s" % (c, filename))

                if len(resp) == 0:
                    resp.append(
                        "No analysis scripts found in %s." % self.analysis_directory)

            return '\n'.join(resp)

        else:
            return self.RESP_HEADER + "ERROR: No such list.\n   Available lists are: %s\n" % LISTS

    def get_machines(self, config):
        """
            Given a config, this will find all of the matching machines on our
            controllers.  It returns a list of controllers and machines for 
            each.
            
            @todo: Code is repeated on controller... Fix this!
        """
        machines = {}
        for c in self.config_list:

            # Get most recent status
            self.config_list[c].get_machines()

            # Does a machine exist to run the profile on?
            machines_c = []
            for m in self.config_list[c].machines:
                tmp_machine = self.config_list[c].machines[m]

                if config == None:
                    machines_c.append(m)
                else:
                    # Profiles Match?
                    m_profile = tmp_machine.config.volatility_profile
                    a_profile = config.volatility_profile

                    # Same type of machines?
                    m_type = tmp_machine.type
                    a_type = config.machine_type

                    # Break when we find a match
                    if m_profile == a_profile and tmp_machine.ALLOCATED < 0 and m_type == a_type:
                        machines_c.append(m)
            if len(machines_c) > 0:
                machines[c] = len(machines_c)

        if len(machines) > 0:
            return machines
        else:
            # No Match?
            return None

    def _send_analysis(self, analysis_name):
        """
            Send analysis to our controller and start it.
        """

    def command_start(self, command):
        """
            Search through all of our machines, calculate how many we want to 
            start at each remote controller, issue the start command and push
            the config that we want to execute
        """

        # Update our analysis list
        self.update_analysis()

        # Figure out which analysis they want to run
        if command.analysis is None:
            logger.error("Must name analysis to start.")
            return self.RESP_HEADER + "ERROR: No analysis name provided."

        if command.analysis not in self.analysis_list.keys():
            return self.RESP_HEADER + "ERROR: Analysis does not exist. Options are: %s" % self.analysis_list.keys()
        else:
            analysis_file = self.analysis_list[command.analysis][1]
            analysis_class = self.analysis_list[command.analysis][0]

        # Did they define a controller?
        if command.controller is not None and command.controller not in self.config_list.keys():
            return self.RESP_HEADER + "ERROR: Controller does not exist. Options are: %s" % self.config_list.keys()

        # Does this analysis involve a binary sample?
        if command.sample_doc_id is not None:
            # Add this analysis to our database
            db_analysis_id = self.DB_analysis.create_analysis(
                command.sample_doc_id, command)
            # update our command
            command.db_analysis_id = db_analysis_id

        # Start all of our analysis on the remote controller
        if command.controller is not None:
            self.config_list[command.controller].send_analysis(analysis_file,
                                                               command)
        else:

            # What machine type are we looking for?
            if command.machine_type is not None:
                machine_type = command.machine_type
            elif analysis_class.MACHINE_TYPE is not None:
                machine_type = analysis_class.MACHINE_TYPE
            else:
                machine_type = None

            # Find a list of controllers with these types of machines
            controllers = []
            # Loop over all of our controllers
            for config in self.config_list:
                controller = self.config_list[config]
                controller.get_machines()
                # Loop over all of the machines on that controller
                for m_name in controller.machines:
                    if controller.machines[m_name].type == machine_type:
                        controllers.append(controller)

            # Did we find any acceptable controllers?
            if len(controllers) == 0:
                logger.error("No controllers found with machines of type %d" %
                             machine_type)
                return self.RESP_HEADER + "No controllers found with machines of type %d" % machine_type

            # Pick a random controller in the list
            rand_idx = random.randint(0, len(controllers) - 1)
            rand_controller = controllers[rand_idx]
            print " * Sending analysis to random controller. (%s)" % rand_controller.name
            rand_controller.send_analysis(analysis_file, command)

        return self.RESP_HEADER + "Machines started successfully."

    def command_abstract(self, command):
        """
            This function processes abstract commands and passes them to the 
            appropriate analysis engine (or all)
        """

        for c in self.config_list:
            self.config_list[c].send_cmd(command)

        logger.debug("Sent abstract command.")

        return self.RESP_HEADER + "Command %s sent successfully." % command.cmd

    def command_splash(self, cmd):
        """ Print splash screen for the CLI """
        ret = []

        # Get our machines
        machines = {}  # self.get_machines(None)

        # Calculate the total number of machines
        total_machines = 0
        for c in machines:
            total_machines += machines[c]
        ret.append(".--------------------------------------------.")
        ret.append("|                                            |")
        ret.append("|          LO-PHI Master Controller          |")
        ret.append("|                                            |")
        ret.append("+--------------------------------------------+")
        ret.append("| -                                        - |")
        ret.append("|            Remote Servers: %-3d             |" % (
        len(self.config_list)))
        ret.append(
            "|           Remote Machines: %-3d             |" % total_machines)
        ret.append("|                  Analyses: %-3d             |" % (
        len(self.analysis_list)))
        ret.append("| -                                        - |")
        ret.append("| -                                        - |")
        ret.append("|     Type 'help' for a list of commands.    |")
        ret.append("| -                                        - |")
        ret.append("`--------------------------------------------'")

        print "Sending Splash Screen"
        # return "Splash!"
        return '\n'.join(ret)

    def command_update_hw(self, cmd):
        """ Update our HW config info, e.g. update the IP for a physical machine sensor """
        # TODO
        pass

    #    def process_cmd(self, type, cmd, corr_id, routing_key):
    def process_cmd(self, cmd):
        """ Generic function to process commands received from amqp and send a response """

        resp = self.COMMANDS[cmd.cmd](cmd)

        logger.debug("Resp: %s" % resp)
        # send to resp_queue
        #        if type == G.CTRL_TYPE:
        #
        #            response = json.dumps((corr_id, routing_key, resp))
        #            logger.debug("Sending response: %s" % response)
        #            self.out_queue.put(response)

        response = cmd.make_response(resp)
        logger.debug("Sending response: %s" % response)
        self.out_queue.put(str(response))

    def start(self):
        """
            Main function to just loop forever while waiting for input over amqp
        """

        quit_commands = ['q', 'quit', 'exit']

        # Setup our handler to close gracefully
        G.set_exit_handler(self.cleanup)

        # Setup or queues
        self.manager = multiprocessing.Manager()
        self.INPUT_QUEUE = self.manager.Queue()

        # set of comm processes (rabbitmq, etc.) - for cleanup later
        self.comm_processes = set([])

        # Set up communication queue with all of our consumers, processes, and producers
        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()


        # Listen for physical cards registering
        #         HOST = ''
        #         PORT = G.CARD_REG_PORT
        #
        #         self.reg_consumer = Card_Reg_Server((HOST, PORT), UDPHandler, self.in_queue)
        #         self.reg_consumer.start()
        #         self.comm_processes.add(self.reg_consumer)

        # Setup RabbitMQ consumers and queues
        logger.debug("Starting up LOPHI RabbitmQ Producers...")

        #         self.ctrl_producer = rabbitmq.LOPHI_RPC_Producer(self.amqp_host,
        #                                                          self.out_queue,
        #                                                          G.RabbitMQ.CTRL_OUT,
        #                                                          G.RabbitMQ.CTRL_IN,
        #                                                          exchange_type=G.RabbitMQ.TYPE_FANOUT,
        #                                                          exchange=G.RabbitMQ.EXCHANGE_FANOUT)
        self.ctrl_producer = rabbitmq.LOPHI_RabbitMQ_Producer(self.amqp_host,
                                                              self.out_queue,
                                                              G.RabbitMQ.CTRL_OUT,
                                                              exchange_type=G.RabbitMQ.TYPE_FANOUT,
                                                              routing_key='',
                                                              exchange=G.RabbitMQ.EXCHANGE_FANOUT)
        self.ctrl_producer.start()
        self.comm_processes.add(self.ctrl_producer)

        logger.debug("Starting up LOPHI RabbitMQ Consumers...")

        # Listen for control messages, e.g. from a CLI
        #         self.ctrl_consumer = rabbitmq.LOPHI_RPC_Consumer(self.amqp_host,
        #                                                          self.in_queue,
        #                                                          G.RabbitMQ.CTRL_IN)
        self.ctrl_consumer = rabbitmq.LOPHI_RabbitMQ_Consumer(self.amqp_host,
                                                              self.in_queue,
                                                              G.RabbitMQ.CTRL_IN)
        self.ctrl_consumer.start()
        self.comm_processes.add(self.ctrl_consumer)

        # Connect to all of our controllers
        for c in self.config_list:
            self.config_list[c].connect()

        print "Waiting for input from queues."

        # Just loop forever taking input from rabbitmq
        while 1:
            user_input = self.in_queue.get()

            # Decode input from rabbitmq format
            try:

                #                (corr_id, routing_key, msg) = json.loads(user_input)

                # type is type of message
                # command
                #                (type, cmd_data) = msg

                cmd = LophiCommand.from_data(user_input)

            except:
                print "Unknown command: ", user_input
                continue

            logger.debug("Received msg %s" % cmd)

            # check if type is valid
            #            if msg.type not in self.MSG_TYPES:
            #                print "Invalid message type: %s\n" % type
            # See if it's valid command
            if cmd.cmd not in self.COMMANDS.keys():
                resp = "Invalid Command: %s\n" % cmd.cmd
                logger.debug(resp)
                response = cmd.make_response(resp)
                self.out_queue.put(response)
            else:
                #                self.process_cmd(type, cmd, corr_id, routing_key)
                self.process_cmd(cmd)

            """ 
                @todo: add command to kill master 
            """


        # Call our cleanup function and shutdown nicely
        self.cleanup(None)

    def cleanup(self, sig, func=None):
        """
            Simple funciton to just close up everything nicely
        """

        print "Closing up shop..."

        # Disconnect all of our remote controllers
        for c in self.config_list:
            self.config_list[c].disconnect()

        # Kill our data handler
        self.INPUT_QUEUE.put(G.CTRL_CMD_KILL)

        # Terminate the consumers and producers
        self.in_queue.put(G.CTRL_CMD_KILL)
        self.out_queue.put(G.CTRL_CMD_KILL)
        for child in self.comm_processes:
            child.stop()
