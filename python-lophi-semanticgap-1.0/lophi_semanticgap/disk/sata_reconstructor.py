"""
    This module helps with reconstructing SATA Frame order due to Native Command Queuing
"""
# Native
from collections import deque
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G
from lophi.data import DiskSensorPacket
from lophi_semanticgap.disk.sata import FrameType, NCQCommandType

class PhysicalPacket(object):
    """
        Intermediate structure for feeding into SATA Reconstructor
    """
    def __init__(self, header, data):
        self.sata_header = header
        self.sata_data = data

class SATAReconstructor:
    """
        Class for reconstructing SATA frames back into semantic order (Native Command Queuing
        reorders SATA frames)
    """

    DEVICE_IDLE = 0
    WAIT_FOR_REGISTER_ACK = 1
    WAIT_FOR_DMA_DATA_DEVICE = 2
    WAIT_FOR_DMA_DATA_HOST = 3

    # TODO split up into host vs device?  Need to figure out
    # how to tell by the Register HTD Frame
    WAIT_FOR_NON_NCQ_DATA = 4

    HOST_TO_DEVICE = 0
    DEVICE_TO_HOST = 1


    def __init__(self, sector_size):

        # superclass init
        #        Process.__init__(self)

        # TODO - get this automatically
        self.sector_size = sector_size

        # queue for sata packets from the host
        self.host_queue = deque([])

        # queue for sata packets from the device
        self.device_queue = deque([])

        # Non NCQ data structures
        # stack for our non NCQ register packets
        self.regular_register_stack = []
        # keep 1 disk sensor packet (since we only have
        # 1 transaction at a time for non NCQ) and aggregate
        self.regular_disk_sensor_packet = None


        # Native Command Queue data structures
        # stack for our NCQ register packets
        self.ncq_register_stack = []

        # Store DMA setup packets to help us correlate data packets with TAGs
        self.ncq_dma_stack = []

        # Store register and data packets for outstanding NCQ transactions
        # indexed by TAG 0 - 31
        # self.ncq_transactions_outstanding stores the Register Frame so we can access the metadata later
        # self.ncq_data_outstanding stores the aggregated data in a DiskSensorPacket
        self.ncq_transactions_outstanding = [None for k in range(32)]
        self.ncq_data_outstanding = [None for k in range(32)]

        # data packet queue for aggregating NCQ packets for a DMA transfer
        self.ncq_data_packets = deque([])
        self.ncq_data_len = 0

        # last packet sequence number - used to see if we lost a packet due to network
        # or other problems
        self.last_packet_seqno = None

        # State
        self.STATE = self.DEVICE_IDLE

        # errors - keep track of how many times we encounter a packet we do not expect
        # in our current STATE
        self.num_errors = 0

        # total frames we have processed
        self.total_frames = 0


    def process_packet(self, physical_packet):
        """
            Takes an incoming LOPHI packet and calls the appropriate
            handler based on the type of SATA frame it is

            Returns either a list of DiskSensorPackets or None
        """

        # Note: Right now when we receive a packet, we process a packet,
        # so we should never have more than 1 packet in the host and device queues combined.
        # When Brendon modifies the SATA sensor hardware to indicate which packets were
        # received in the same clock cycle, we will need to add code here to
        # infer state based on what packets we see, which may require processing multiple packets
        # in our queues.

        # Note: looks like maybe there is no hardware problem now, so we may never need to do the above

        self.total_frames += 1

        # Extract our data
        sata_header = physical_packet.sata_header
        sata_data = physical_packet.sata_data

        # Show what state we are in
        if self.STATE == self.DEVICE_IDLE:
            logger.debug("STATE DEVICE IDLE: Received %d: %s" % (sata_header['lophi_seqn'], FrameType.type_lookup[sata_header['type']]))
            if sata_header['type'] == 0x46: # data
                logger.debug("DATA packet data length is %d" % len(sata_data[:-4]))
        elif self.STATE == self.WAIT_FOR_REGISTER_ACK:
            logger.debug("STATE WAIT For REGISTER ACK: Received %d: %s" % (sata_header['lophi_seqn'], FrameType.type_lookup[sata_header['type']]))
        elif self.STATE == self.WAIT_FOR_DMA_DATA_DEVICE:
            logger.debug("STATE WAIT For DMA DATA from DEVICE: Received %d: %s" % (sata_header['lophi_seqn'], FrameType.type_lookup[sata_header['type']]))
        elif self.STATE == self.WAIT_FOR_DMA_DATA_HOST:
            logger.debug("STATE WAIT For DMA DATA from HOST: Received %d: %s" % (sata_header['lophi_seqn'], FrameType.type_lookup[sata_header['type']]))
        elif self.STATE == self.WAIT_FOR_NON_NCQ_DATA:
            logger.debug("STATE WAIT for NON NCQ DATA: Received %d: %s" % (sata_header['lophi_seqn'], FrameType.type_lookup[sata_header['type']]))
        else:
            logger.debug("UNKNOWN STATE: Received %d: %s" % (sata_header['lophi_seqn'], FrameType.type_lookup[sata_header['type']]))



        # check for dropped packet
        if self.last_packet_seqno:

            if sata_header['lophi_seqn'] == (self.last_packet_seqno + 1) % 65536:
                # no dropped packet (at least due to network)
                self.last_packet_seqno = sata_header['lophi_seqn']
            else:
                # We have at least one missing packet
                # Need to flush all state, etc.
                logger.error("Encountered dropped packet.  Resetting state.")
                self._reset_state()

        else: # first packet we've seen
            self.last_packet_seqno = sata_header['lophi_seqn']


        # Ignore DMA Activate, BIST Activate frames for now
        if sata_header['type'] == FrameType.DMAActivateFIS or sata_header['type'] == FrameType.BISTActivateFIS:
            return None


        # now process the next packet from the queue

        source = "HOST" if sata_header['direction'] == self.HOST_TO_DEVICE else "DEVICE"

        # States
        # IDLE - waiting for a new frame to setup a new transaction or DMA transfer, etc.
        # WAITING for Register ACK - we got a Register HTD Frame indicating a new transaction,
        #      expect the device to send a register DTH back, except for special circumstances
        # WAITING for DMA data from device - got a DMA setup packet, waiting for DMA data from device
        # WAITING for DMA data from the host - got a DMA setup packet, waiting for DMA data from host
        # WAITING for Non-NCQ data

        # First, check if the device sent a SET DEVICE BITS Frame
        # This might indicate that the device ran into an error
        # and we have to reset state

        if sata_header['type'] == FrameType.SetDeviceBitsFIS:
            return self.handle_set_device_bits(physical_packet)

        # Check if it is a register HTD packet
        # From our observations, apparently these can come at any time
        # even between DMA setup packets and DMA data packets
        if (sata_header['direction'] == self.HOST_TO_DEVICE and
                    sata_header['type'] == FrameType.RegisterFIS_HtoD):

            return self.handle_register_HTD(physical_packet)

        # Check if it is a register DTH packet
        # this function will ignore it unless it announces an error
        if (sata_header['direction'] == self.DEVICE_TO_HOST and
                    sata_header['type'] == FrameType.RegisterFIS_DtoH):

            return self.handle_ncq_register_DTH(physical_packet)

        # PIO Setup Frames only come from the device
        # Currently we have no way of knowing when they will come ahead of time -- should
        # be indicated by the Register Frame, but that is unknown
        elif sata_header['type'] == FrameType.PIOSetupFIS:
            return self.handle_pio_setup(physical_packet)

        ## IDLE state
        elif self.STATE == self.DEVICE_IDLE:

            # check for new Register Packet HTD or DMA Setup from Host

            # try to pull a new register packet from host queue
            # or DMA setup packet from the host queue

            # Check if it is a register HTD packet
            if (sata_header['direction'] == self.HOST_TO_DEVICE and
                        sata_header['type'] == FrameType.RegisterFIS_HtoD):

                return self.handle_register_HTD(physical_packet)

            # Try ignoring DMA Setups from Host for now
            # Doesn't look like it gets used for NCQ?

            elif (sata_header['direction'] == self.HOST_TO_DEVICE and
                          sata_header['type'] == FrameType.DMASetupFIS):
                logger.debug("IDLE State: Received DMA Setup from %s.  Ignoring." % source)

                # Didn't get a Register or DMA setup frame in the host queue
                # Check the device queue for DMA setup frame
            elif (sata_header['direction'] == self.DEVICE_TO_HOST and
                          sata_header['type'] == FrameType.DMASetupFIS):

                return self.handle_dma_setup(physical_packet)


            else:
                logger.error("IDLE State: Expected Register HTD or DMA Setup frame from Device but got type %s from %s." % (FrameType.type_lookup[physical_packet.sata_header['type']], source))
                return None


        elif self.STATE == self.WAIT_FOR_REGISTER_ACK:
            # We got a HTD register frame, so we need the DTH Register frame to acknowledge
            # the new transaction

            if (sata_header['direction'] == self.DEVICE_TO_HOST and
                        sata_header['type'] == FrameType.RegisterFIS_DtoH):

                return self.handle_ncq_register_DTH(physical_packet)

            else:
                # Wrong type of frame

                logger.error("WAITING FOR NCQ REGISTER ACK State: Expected Register DTH ACK but got type %s from %s." % (FrameType.type_lookup[physical_packet.sata_header['type']], source))
                return self._handle_unexpected_packet(physical_packet)

                #return None

        elif self.STATE == self.WAIT_FOR_DMA_DATA_DEVICE:

            if (sata_header['direction'] == self.DEVICE_TO_HOST and
                        sata_header['type'] == FrameType.DataFIS):

                return self.handle_ncq_data_packet(physical_packet)

            else: # wrong Frame Type

                logger.error("WAITING FOR DMA DATA from Device State: Expected Data Frame from Device but got type %s from %s." % (FrameType.type_lookup[physical_packet.sata_header['type']], source))

                # reset len
                self.ncq_data_len = 0

                # clear the aggregation queue
                self.ncq_data_packets.clear()

                # pop the DMA setup packet stack
                self.ncq_dma_stack.pop()

                return self._handle_unexpected_packet(physical_packet)
                #return None


        elif self.STATE == self.WAIT_FOR_DMA_DATA_HOST:

            if (sata_header['direction'] == self.HOST_TO_DEVICE and
                        sata_header['type'] == FrameType.DataFIS):

                return self.handle_ncq_data_packet(physical_packet)

            else:
                logger.error("WAITING FOR DMA DATA from HOST State: Expected Data Frame from Host but got type %s from %s." % (FrameType.type_lookup[physical_packet.sata_header['type']], source))

                # reset len
                self.ncq_data_len = 0

                # clear the aggregation queue
                self.ncq_data_packets.clear()

                # pop the DMA setup packet stack
                self.ncq_dma_stack.pop()

                return self._handle_unexpected_packet(physical_packet)
                #return None


        elif self.STATE == self.WAIT_FOR_NON_NCQ_DATA:
            # We got a Non NCQ HTD Register frame, so we simply just wait for data

            # check if we have a DATA frame

            # TODO how do we tell which way that DATA frames should be going?
            # Does the Register HTD packet have this info?

            if sata_header['type'] == FrameType.DataFIS:
                return self.handle_non_ncq_data_packet(physical_packet)

            else:
                logger.error("WAITING FOR NON NCQ DATA State: Expected Data Frame but got type %s from %s" % (FrameType.type_lookup[physical_packet.sata_header['type']], source))
                return self._handle_unexpected_packet(physical_packet)


        else: # UNKNOWN state
            logger.error("Unknown state in Sata Reconstructor state machine!")
            return None

    def _handle_unexpected_packet(self, physical_packet):
        """
        Handles unexpected packet

        Puts self back into DEVICE_IDLE STATE
        """
        # increment error
        self.num_errors += 1

        logger.error("Errors/Total Frames: %d/%d.  Returning to DEVICE IDLE state." % (self.num_errors, self.total_frames))

        # return to IDLE state
        self.STATE = self.DEVICE_IDLE

        logger.error("Trying to handle unexpected packet.")

        frame_type = physical_packet.sata_header['type']

        # Check if it is a register packet HTD
        if frame_type == FrameType.RegisterFIS_HtoD:
            logger.error("Processing Register HTD packet anyway.")
            return self.handle_register_HTD(physical_packet)

        #                    Try ignoring DMA Setups from Host for now
        #                    Doesn't look like it gets used for NCQ?

        #                    elif frame_type == FrameType.DMASetupFIS:
        #                        self.handle_dma_setup(physical_packet)
        #

        elif frame_type == FrameType.DMASetupFIS:
            return self.handle_dma_setup(physical_packet)

        else:
            pass

        return None


    def _reset_state(self):
        """
            Resets state if we have a dropped packet or out of order, etc.
        """

        #TODO what else does this function need to do?

        logger.error("Detected dropped or out of order packet.  Resetting our state machine to DEVICE IDLE.  You may continue to get errors about receiving the wrong types of Frames.")

        # Reset the last seqno seen
        self.last_packet_seqno = None


        # Reset outstanding DMA setup packets
        self.ncq_dma_stack = []

        # Reset outstanding NCQ transactions for all TAGs
        self.ncq_transactions_outstanding = [None for k in range(32)]
        self.ncq_data_outstanding = [None for k in range(32)]

        # Reset any data if we were in the middle of a DMA transfer
        self.ncq_data_packets = deque([])
        self.ncq_data_len = 0

        # Set state to IDLE
        self.STATE = self.DEVICE_IDLE




    def handle_set_device_bits(self,physical_packet):
        """
            Given a Set Device Bits frame, this will check to see if we have
            to react in anyway to the command

            @param physical_packet: packet with physical SATA info extracted.

            returns either a list of DiskSensorPackets or None
        """


        # Extract useful info
        status_lo = physical_packet.sata_header['status_lo']
        ACT = physical_packet.sata_header['proto']
        interrupt = physical_packet.sata_header['interrupt']

        # Was there an error?
        if status_lo & 1 == 1:
            logger.error("Got a Set Device Bits error, throwing away ALL outstanding NCQ commands.")
            self._reset_ncq()
            return None

        # Check for Queued Error Log Set Device Bits (see 13.6.3.4)
        if interrupt == 1 and ACT == 0xffffffff: # if all bits are set to one, we are aborting all outstanding commands
            logger.error("Got a Set Device Bits Response to read the Queued Error Log (we think).  Throwing away ALL outstanding NCQ commands.")
            self._reset_ncq()
            return None

        # Check for status update
        if interrupt == 1 and ACT != 0:
            logger.debug("Got a Set Device Bits packet indicating successful NCQ commands completed.")
            logger.debug("ACT: " + "{:032b}".format(ACT))

            # From our observations, apparently these can come several commands
            # after the original transactions, so we do NOT flush
            # and change state to IDLE

            return None

            # ret = []
            #
            # # determine which queued commands were successful
            # for i in range(32):
            #     if (ACT & (1 << i) != 0):
            #         # flush out this command
            #         logger.debug("Flushing data for TAG %d" % i)

            #         # add data from self.ncq_data_outstanding to return list
            #         ret.append(self.ncq_data_outstanding[i])

            #         self.ncq_transactions_outstanding[i] = None
            #         self.ncq_data_outstanding[i] = None

            # # set state to IDLE
            # self.STATE = self.DEVICE_IDLE

            # # return
            # return ret

        # else, we don't know what this Frame is for
        logger.error("Got a Set Device Bits Frame, but we don't know what it is for.")

        return None


    def _reset_ncq(self):
        """
            Resets all NCQ state in response to an NCQ error
        """

        logger.error("Resetting state of all NCQ data structures in response to an NCQ error or dropped/missing packets")

        # Reset the stack for our outstanding NCQ register packets waiting for a Register DTH
        self.ncq_register_stack = []

        # Reset our array of outstanding NCQ transactions
        self.ncq_transactions_outstanding = [None for k in range(32)]

        # Flush all the partially completed Disk Sensor Packets
        for i in range(32):
            if self.ncq_data_outstanding[i]:
                logger.debug("Flushing data for TAG %d" % i)
            #                self.out_queue.put(self.ncq_data_outstanding[i])
        self.ncq_data_outstanding = [None for k in range(32)]

        # Store DMA setup packets to help us correlate data packets with TAGs
        self.ncq_dma_stack = [];

        # data packet queue for aggregating NCQ packets for a DMA transfer
        self.ncq_data_packets.clear()
        self.ncq_data_len = 0



    def handle_register_HTD(self, register_packet):
        """
            Handle a Register HTD

            Always returns None
        """

        sata_header = register_packet.sata_header

        # Check if C bit is set to 0 -- see 11.2 Dl1 Note 1 -- no FIS is sent
        # I think we can ignore if C bit is set to 0 and go back to IDLE state
        # software reset could still happen -- not sure which bit is the SRST bit in the control register?
        if sata_header['C'] == 0:
            logger.debug("Got HTD Register Packet but C bit is set to 0.  Ignoring.")
            return None

        # check if this is an NCQ command
        if sata_header['command'] == NCQCommandType.ReadFPDMAQueued or sata_header['command'] == NCQCommandType.WriteFPDMAQueued:

            cmd = "READ"
            direction = G.SATA_OP.DIRECTION.READ
            if sata_header['command'] == NCQCommandType.WriteFPDMAQueued:
                cmd = "WRITE"
                direction = G.SATA_OP.DIRECTION.WRITE

            # NCQ uses features field for sector count
            logger.debug("Got HTD Register Packet for NCQ %s -- TAG %d expecting %d bytes." % (cmd, sata_header['tag'], sata_header['features']*self.sector_size))

            #            if len(self.ncq_register_stack) > 0:
            #                logger.error("Our NCQ register stack will be greater than 1, so we have at least one outstanding NCQ register packet with NO Register ACK.  Stack size is %d" % len(self.ncq_register_stack))

            #            # add to our stack
            #            self.ncq_register_stack.append(register_packet)

            #No ACKS
            #            # change state to waiting for Register DTH
            #            self.STATE = self.WAIT_FOR_REGISTER_ACK
            #
            #            # deal with error checking when we get the Register DTH ACK back
            #            return None

            # check if the spot belonging to the associated TAG is empty
            if (not self.ncq_transactions_outstanding[sata_header['tag']]):
                # This TAG is not taken, so we just add
                self.ncq_transactions_outstanding[sata_header['tag']] = register_packet

            else:
                logger.error("Received HTD NCQ Register Packet for TAG %d but it is already in use.  Using it anyway." % sata_header['tag'])
                # still put it in there for now
                self.ncq_transactions_outstanding[sata_header['tag']] = register_packet

                #don't need this if we accept the register packet anyway
                #return None


            # Associate this DTH Register packet
            # with the tag and prepare the disk sensor packet for aggregating data
            lba = sata_header['lba']

            # NOTE: NCQ uses features field instead of count for sector count
            sector_count = sata_header['features']


            disk_sensor_packet = DiskSensorPacket()
            disk_sensor_packet.sector = lba
            disk_sensor_packet.num_sectors =  sector_count
            disk_sensor_packet.disk_operation = direction
            disk_sensor_packet.size = sector_count*self.sector_size
            disk_sensor_packet.data = ""

            self.ncq_data_outstanding[sata_header['tag']] = disk_sensor_packet

            # DO NOT set state to IDLE
            # Because now it looks like Register packets can come during other times
            # so we want to maintain the current state
            #            # set state to IDLE
            #
            #            self.STATE = self.DEVICE_IDLE

            return None



        # NCQ Management stuff
        elif sata_header['command'] == NCQCommandType.NCQQueueManagement:
            logger.debug("Got Register Packet for NCQ Queue Management.  Ignoring for now.")
            # Don't need to change state
            return None

        # NON NCQ Register Packet
        else:
            logger.debug("Got Non-NCQ HTD Register Packet, expected %d bytes." % (sata_header['count']*self.sector_size))
            logger.debug("Command field is %d" % sata_header['command'])

            #            if len(self.ncq_register_stack) > 0:
            #                logger.error("Have more than 0 outstanding NCQ HTD Register Packets.  Non NCQ Register packets are not supposed to be sent while NCQ Register packets are still outstanding.  Size of stack is %d" % len(self.regular_register_stack))


            #            if len(self.regular_register_stack) > 0:
            #                logger.error("Will have more than one outstanding regular (non NCQ) HTD Register Packets.  Size of stack is %d" % len(self.regular_register_stack))

            # push this normal Register HTD packet on the stack
            self.regular_register_stack.append(register_packet)


            # prepare the disk sensor packet for aggregating data
            lba = sata_header['lba']
            sector_count = sata_header['count']
            direction = sata_header['direction']

            #             self.regular_disk_sensor_packet = DiskSensorPacket(lba,
            #                                          sector_count,
            #                                          direction,
            #                                          sector_count*self.sector_size,
            #                                          "")
            self.regular_disk_sensor_packet = DiskSensorPacket()
            self.regular_disk_sensor_packet.sector = lba
            self.regular_disk_sensor_packet.num_sectors = sector_count
            self.regular_disk_sensor_packet.disk_operation = direction
            self.regular_disk_sensor_packet.size = sector_count*self.sector_size
            self.regular_disk_sensor_packet.data = ""

            # Transition state now that we are waiting for data
            self.STATE = self.WAIT_FOR_NON_NCQ_DATA

            return None



    def handle_ncq_register_DTH(self, register_packet):
        """
            Handle a Register DTH frame (an ACK)
            Always returns None
        """

        sata_header = register_packet.sata_header

        frame_type = sata_header['type']


        logger.debug("Received DTH Register Packet.")

        # Check for an error
        if register_packet.sata_header['status'] & 1 == 1:
            logger.error("DTH Register Packet indicates ATA error code: %d.  All outstanding commands will be aborted after Host sends request to read the Queued Error Log." % register_packet.sata_header['error'])

            # TODO reset state?
            self._reset_ncq()

        return None

    # NO ACKs
    #        # If there are NCQ transactions outstanding, then this must be for acknowledging
    #        # queuing of the last NCQ command
    #
    #        # check if our ncq register stack is non empty
    #        if len(self.ncq_register_stack) > 0:
    #
    #            # pop the first ncq register off the stack
    #            last_reg_packet = self.ncq_register_stack.pop()
    #
    #            # check that last register was a register HTD
    #            if last_reg_packet.sata_header['type'] != FrameType.RegisterFIS_HtoD:
    #                logger.error("Got a DTH Register Packet (ACK) but previous Register Packet was NOT a HTD.  Ignoring.")
    #                return None
    #
    #            last_sata_header = last_reg_packet.sata_header

    #             # check if the spot belonging to the associated TAG is empty
    #             if (not self.ncq_transactions_outstanding[last_sata_header['tag']]):
    #                 # This TAG is not taken, so we just add
    #                 self.ncq_transactions_outstanding[last_sata_header['tag']] = last_reg_packet

    #             else:
    #                 logger.error("Received DTH NCQ Register Packet for TAG %d but it is already in use." % last_sata_header['tag'])
    #                 # still put it in there for now
    #                 self.ncq_transactions_outstanding[last_sata_header['tag']] = last_reg_packet

    #                 #TODO reset state?

    #                 return None


    #             # Associate this DTH Register packet
    #             # with the tag and prepare the disk sensor packet for aggregating data
    #             lba = last_sata_header['lba']

    #             # NOTE: NCQ uses features field instead of count for sector count
    #             sector_count = last_sata_header['features']
    #             direction = last_sata_header['direction']

    # #             disk_sensor_packet = DiskSensorPacket(lba,
    # #                                          sector_count,
    # #                                          direction,
    # #                                          sector_count*self.sector_size,
    # #                                          "")

    #             disk_sensor_packet = DiskSensorPacket()
    #             disk_sensor_packet.__setattr__('sector', lba)
    #             disk_sensor_packet.__setattr__('num_sectors', sector_count)
    #             disk_sensor_packet.__setattr__('disk_operation', direction)
    #             disk_sensor_packet.__setattr__('size', sector_count*self.sector_size)
    #             disk_sensor_packet.data = ""

    #             self.ncq_data_outstanding[last_sata_header['tag']] = disk_sensor_packet

    #             logger.debug("Associating DTH Register Packet (ACK) with TAG %d.  Expecting %d bytes." % (last_sata_header['tag'], sector_count*self.sector_size))

    #             # set state to IDLE

    #             self.STATE = self.DEVICE_IDLE

    #             return None


    def handle_non_ncq_register_DTH(self, physical_packet):
        """
            Seeing a non-NCQ Register DTH Frame indicates the successful
            completion of a non-NCQ command

            returns either None or a list with a single DiskSensorPacket (only in corner cases)
        """

        ret = None

        # This marks the successful completion of a non NCQ command
        if len(self.regular_register_stack) > 0:

            # pop the stack
            self.regular_register_stack.pop()

            # deal with the aggregated data and put it in the outgoing queue
            # This should already have been done when we do a size check whenever
            # we get a DATA frame, but this is just in case
            if self.regular_disk_sensor_packet:
                logger.debug("Flushing data for normal NCQ transaction.")

                ret = [self.regular_disk_sensor_packet]

                self.regular_disk_sensor_packet = None

            self.state = self.DEVICE_IDLE

        else:
            # We don't have a packet to match this up with

            pass

        return ret




    # PIO Setups (non NCQ)
    def handle_pio_setup(self, pio_setup_packet):
        """
            Handles PIO Setup packets

            Always returns None
        """

        logger.debug("Received a PIO Setup Frame expecting %d bytes." % pio_setup_packet.sata_header['transfer_count'])

        # change state to receive PIO data
        if self.STATE != self.WAIT_FOR_NON_NCQ_DATA:
            logger.error("Got a PIO Setup Packet but state was not WAITING FOR NON NCQ DATA.  Changing state to WAITING FOR NON NCQ DATA.")

        self.STATE = self.WAIT_FOR_NON_NCQ_DATA

        return None


    # DMA Setup packets are only used for NCQ
    def handle_dma_setup(self, dma_setup_packet):
        """
            Handles DMA Setup Packets

            Always returns None
        """


        # check if we already have packets in this stack
        if len(self.ncq_dma_stack) > 0:
            logger.debug("Received a DMA setup packet (for NCQ) but have outstanding DMA setup commands.  Stack size is %d" % len(self.ncq_dma_stack))

        tag = dma_setup_packet.sata_header['dma_buf_identifier_low']
        data_len = dma_setup_packet.sata_header['transfer_count']

        logger.debug("Received a DMA setup packet (for NCQ) for TAG %d expecting %d bytes." % (tag, data_len))

        # add to our stack
        self.ncq_dma_stack.append(dma_setup_packet)

        # Now we are waiting for data
        # Depends on the direction_bit, NOT the LOPHI direction
        # Hypothesis is that NCQ only uses DMA Setups from the Device
        if dma_setup_packet.sata_header['direction_bit'] == self.HOST_TO_DEVICE:
            logger.debug("DMA setup packet was for a WRITE - direction_bit == %d" % dma_setup_packet.sata_header['direction_bit'])
            # Host will send data to write
            self.STATE = self.WAIT_FOR_DMA_DATA_HOST

        else:
            logger.debug("DMA setup packet was for a READ - direction_bit == %d" % dma_setup_packet.sata_header['direction_bit'])
            self.STATE = self.WAIT_FOR_DMA_DATA_DEVICE

        return None



    def handle_ncq_data_packet(self, data_packet):
        """
            Handle Data Frame associated with an NCQ transaction

            Always returns None
        """

        # Check if we have an NCQ transaction (DMA) pending
        if len(self.ncq_dma_stack) > 0:
            logger.debug("Received a data packet for (NCQ)")

            dma_setup_packet = self.ncq_dma_stack[-1]

            tag = dma_setup_packet.sata_header['dma_buf_identifier_low']

            # Check the register packet
            register_packet = self.ncq_transactions_outstanding[tag]
            if not register_packet:
                logger.error("NCQ Data packet with TAG %d does not correspond to an observed Register packet.  Ignoring." % tag)
                return None

            # Data is the data just observed without the 4 byte checksum
            data = data_packet.sata_data[:-4]
            direction = data_packet.sata_header['direction']

            # NOTE - with the state based design, I don't think we need to check direction anymore

            # check direction
            # TODO make sure it is direction_bit we care about
            #             if direction == dma_setup_packet.sata_header['direction']:
            #                 logger.error("Received NCQ DATA packet with direction %d but expected %d from DMA setup packet.  Ignoring." % (direction, dma_setup_packet.sata_header['direction']+1 % 0))
            #                 return

            # Add to our queue
            self.ncq_data_packets.append(data_packet)

            logger.debug("Added DATA packet to our queue. (%d -> %d of %d)"%(self.ncq_data_len,
                                                                             self.ncq_data_len + len(data),
                                                                             dma_setup_packet.sata_header['transfer_count']))

            # check if we got the amount of data indicated by the dma setup packet
            self.ncq_data_len += len(data)

            if self.ncq_data_len >= dma_setup_packet.sata_header['transfer_count']:
                if self.ncq_data_len == dma_setup_packet.sata_header['transfer_count']:
                    logger.debug("Received exactly the amount of data we expected from DMA setup packet.")
                else:
                    logger.error("Received more data than we expected from DMA setup packet.  Aggregating anyway.")

                # Get the DiskSensorPacket that we are using to aggregate data for this transaction
                disk_sensor_packet = self.ncq_data_outstanding[tag]
                for d_packet in self.ncq_data_packets:
                    disk_sensor_packet.data += d_packet.sata_data[:-4]
                #                    disk_sensor_packet.disk_operation = d_packet.sata_header['direction']

                # put it back in the appropriate position in ncq_databuffer
                self.ncq_data_outstanding[tag] = disk_sensor_packet

                # reset len
                self.ncq_data_len = 0

                # clear the aggregation queue
                self.ncq_data_packets.clear()

                # pop the stack
                self.ncq_dma_stack.pop()

                # set state back to IDLE
                self.STATE = self.DEVICE_IDLE


                # Check if we received all the data we meant to receive from the REGISTER packet
                # We flush here because we can't rely on Set Device Bits to come at the proper time
                if len(disk_sensor_packet.data) >= disk_sensor_packet.size:

                    if len(disk_sensor_packet.data) > disk_sensor_packet.size:
                        logger.error("Received more data for TAG %d than expected: %d of %d bytes.  Flushing anyway." % (tag,
                                                                                                                         len(disk_sensor_packet.data),
                                                                                                                         disk_sensor_packet.size))

                    logger.debug("Received %d of %d bytes for TAG %d.  Flushing." % (len(disk_sensor_packet.data),
                                                                                     disk_sensor_packet.size,
                                                                                     tag))

                    ret = []

                    # add data from self.ncq_data_outstanding to return list
                    ret.append(disk_sensor_packet)

                    self.ncq_transactions_outstanding[tag] = None
                    self.ncq_data_outstanding[tag] = None

                    return ret

            else: # we still expect more Data Frames for this DMA Setup Frame

                return None

        else:

            # No DMA Setup Frame outstanding

            # TODO

            logger.error("Received Data Packet while in WAITING for DMA DATA state, but no outstanding DMA Setup Frame.")


        return None



    def handle_non_ncq_data_packet(self, data_packet):
        """
            Handles DATA Frames sent as part of a non-NCQ transaction

            Returns either None or a list with a single DiskSensorPacket
        """

        ret = None

        if len(self.regular_register_stack) > 0:
            logger.debug("Received DATA packet (normal non-NCQ) (%d -> %d)" % (len(self.regular_disk_sensor_packet.data), len(self.regular_disk_sensor_packet.data) + len(data_packet.sata_data[:-4])))

            self.regular_disk_sensor_packet.data += data_packet.sata_data[:-4]
            #            self.regular_disk_sensor_packet.disk_operation = data_packet.sata_header['direction']

            # check if we got all the data we expected for the corresponding register packet
            # we need to do this b/c PIO data transfers don't use a Register ACK to indicate end of the transaction
            # whereas non NCQ DMA setups do

            if len(self.regular_disk_sensor_packet.data) >= self.regular_disk_sensor_packet.size:
                if len(self.regular_disk_sensor_packet.data) > self.regular_disk_sensor_packet.size:
                    logger.error("Got more data than we expected for our non NCQ disk sensor packet.  Flushing anyway.")

                logger.debug("Flushing data for non NCQ disk sensor packet.")

                # Set our direction based on the actual direction that the data came
                self.regular_disk_sensor_packet.direction = data_packet.sata_header['direction']

                # Return our disk sensor packet
                ret = [self.regular_disk_sensor_packet]

                # Reset state
                self.regular_disk_sensor_packet = None
                self.STATE = self.DEVICE_IDLE

        else:
            logger.error("Got a DATA packet while expecting Non NCQ transaction, but there are no outstanding Non NCQ transactions.  Ignoring.")

        return ret
