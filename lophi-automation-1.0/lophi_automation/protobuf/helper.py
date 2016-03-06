"""
    These are helper functions to facilitate sending and receiving Google 
    Protocol Buffers

    (c) 2015 Massachusetts Institute of Technology
"""

import logging
logger = logging.getLogger(__name__)

from lophi_automation.protobuf import machines_pb2
from lophi_automation.protobuf import sensor_output_pb2
from lophi_automation.protobuf import cards_pb2
from lophi_automation.protobuf import analysis_pb2
from lophi_automation.protobuf import rabbitmq_pb2

import lophi.globals as G


def pack_rabbitmq(cmd, args):
    """
       Pack rabbitmq_message 
    """

    # Init proto buffer
    msg = rabbitmq_pb2.RabbitMQ()
    msg.cmd = cmd
    msg.args.extend(args)

    return msg.SerializeToString()


def unpack_rabbitmq(msg_buff):
    """
       Unpack rabbitmq_message
    """
    msg = rabbitmq_pb2.RabbitMQ()
    msg.ParseFromString(msg_buff)

    return (msg.cmd, msg.args)


def pack_card_list(card_config_dict):
    """
        Given a dict of card_configs, this packs up to send to a 
        LOPHI control server 
    """

    # Init proto buffer
    cards = cards_pb2.CardConfigList()

    # Add stuff
    for card_id in card_config_dict:
        card_config2 = cards.card_config.add()

        card_config = card_config_dict[card_id]

        if card_config:
            card_config2.type = card_config.opcode
            card_config2.card_id = card_id
            card_config2.capability_bitvector = card_config.capability_bitvector
            card_config2.ip = card_config.ip
            card_config2.is_registered = True
            
        else:  # No record in the Card Reg Server
            card_config2.type = 0x00
            card_config2.card_id = card_id
            card_config2.capability_bitvector = 0b00000000
            card_config2.ip = '0.0.0.0'
            card_config2.is_registered = False

    return cards.SerializeToString()


def unpack_card_list(card_list_buf):
    """
        Given serialized list of card_configs, convert back.
    """
    # get out protocol buffer
    card_list = cards_pb2.CardConfigList()
    card_list.ParseFromString(card_list_buf)

    # create new dict to add card_configs to
    card_dict = {}
    for card_config in card_list.card_config:
        if card_config.is_registered:
            card_dict[card_config.card_id] = card_config

    return card_dict


def pack_machine_list(machine_list):
        """
            Given our list of machines will pack up a minimal version to send
            to our master controller
        """

        # Init our protocol buffer
        machines = machines_pb2.MachineList()

        # Add required elements
        for m in machine_list.itervalues():
            m2 = machines.machine.add()
            if m.ALLOCATED is None:
                m2.ALLOCATED = -1
            else:
                m2.ALLOCATED = m.ALLOCATED
            m2.config.name = m.config.name
            m2.type = int(m.type)
            if m.config.volatility_profile is not None:
                m2.config.volatility_profile = m.config.volatility_profile
            else:
                m2.config.volatility_profile = ""

        # Serialize and return
        return machines.SerializeToString()

def unpack_machine_list(machine_list_buf):
    """
        Given a serialized version of our list of machines will convert them
        back to the format used on the remote server to keep the code nice and
        consistent
    """
    # Get out protocol buffer
    machine_list = machines_pb2.MachineList()
    machine_list.ParseFromString(machine_list_buf)

    # Create a new list to add the lsit of machines to
    tmp = {}
    for m in machine_list.machine:
        tmp[m.config.name] = m

    # Return new list indexed by name
    return tmp

def pack_analysis_list(anlaysis_list):
        """
            Given our list of active analysis will pack up a minimal version to 
            send to our master controller
        """

        # Init our protocol buffer
        analyses = analysis_pb2.AnalysisList()

        try:
            # Add required elements
            for a in anlaysis_list:
                # Get config
                ac = anlaysis_list[a]
                # Create a new object
                a2 = analyses.analysis.add()
                # Fill values
                a2.analysis_id = a
                a2.lophi_name = ac.lophi_config.name
                a2.machine_type = ac.machine.MACHINE_TYPE
                a2.machine_name = ac.machine.config.name
                a2.volatility_profile = ac.lophi_config.volatility_profile
                a2.created = ac.created
        except:
            G.print_traceback()

        # Serialize and return
        return analyses.SerializeToString()

def unpack_analysis_list(buf_list):
    """
        Given a serialized version of our list of machines will convert them
        back to the format used on the remote server to keep the code nice and
        consistent
    """
    # Get out protocol buffer
    analysis_list = analysis_pb2.AnalysisList()
    analysis_list.ParseFromString(buf_list)

    # Create a new list to add the lsit of machines to
    tmp = {}
    for a in analysis_list.analysis:
        tmp[a.analysis_id] = a

    # Return new list indexed by name
    return tmp


def pack_sensor_output(sensor_output):
#                        output['MODULE_NAME'] = plugin_name
#                        output['SUA_NAME'] = self.lophi_config.name
#                        output['SUA_PROFILE'] = self.lophi_config.volatility_profile
#                        output['MACHINE'] = self.machine.config.name
    sensor_pb2 = sensor_output_pb2.SemanticOutput()
    sensor_pb2.INFO.MODULE = sensor_output['MODULE'];
    sensor_pb2.INFO.SENSOR = sensor_output['SENSOR'];
    sensor_pb2.INFO.PROFILE = sensor_output['PROFILE'];
    sensor_pb2.INFO.MACHINE = sensor_output['MACHINE'];

    for h in sensor_output['HEADER']:
        h_new = sensor_pb2.HEADER.column.add()
        h_new.name = G.volatilty_to_str(h)

    for d in sensor_output['DATA']:
        d_list = sensor_pb2.DATA.add()
        for d2 in d:
            d_item = d_list.item.add()
            d_item.value = G.volatilty_to_str(d2)
         
    try:   
        return sensor_pb2.SerializeToString()
    except:
        logger.error("Could not encode: ",rtn)
        return None


def unpack_sensor_output(sensor_pb2_buf):
#                        output['MODULE_NAME'] = plugin_name
#                        output['SUA_NAME'] = self.lophi_config.name
#                        output['SUA_PROFILE'] = self.lophi_config.volatility_profile
#                        output['MACHINE'] = self.machine.config.name
    sensor_pb2 = sensor_output_pb2.SemanticOutput()
    sensor_pb2.ParseFromString(sensor_pb2_buf)

    sensor_output = {}
    sensor_output['MODULE'] = sensor_pb2.INFO.MODULE
    sensor_output['SENSOR'] = sensor_pb2.INFO.SENSOR
    sensor_output['PROFILE'] = sensor_pb2.INFO.PROFILE
    sensor_output['MACHINE'] = sensor_pb2.INFO.MACHINE

    sensor_output['HEADER'] = []
    for h in sensor_pb2.HEADER.column:
        sensor_output['HEADER'].append(h.name)

    sensor_output['DATA'] = []
    for d in sensor_pb2.DATA:
        tmp = []
        for d2 in d.item:
            tmp.append(d2.value)
        sensor_output['DATA'].append(tmp)

    return sensor_output


