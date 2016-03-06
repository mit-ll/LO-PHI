"""
    This class helps with SATA extraction for the physical disk sensor.
"""
# Native
from collections import deque
from multiprocessing import Process
import struct
import sys
import time
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G


class FrameType:
    RegisterFIS_HtoD = 0x27
    RegisterFIS_DtoH = 0x34
    DMAActivateFIS = 0x39
    DMASetupFIS = 0x41
    DataFIS = 0x46
    BISTActivateFIS = 0x58
    PIOSetupFIS = 0x5f
    SetDeviceBitsFIS = 0xa1
    
    type_lookup = {0x27 : "Register HTD",
                   0x34 : "Register DTH",
                   0x39 : "DMA Activate",
                   0x41 : "DMA Setup",
                   0x46 : "DATA",
                   0x58 : "BIST Activate",
                   0x5f : "PIO Setup",
                   0xa1 : "Set Device Bits"}

class NCQCommandType:
    # Tag is count[7:3]
    ReadFPDMAQueued = 0x60
    WriteFPDMAQueued = 0x61
    NCQQueueManagement = 0x63
    # TODO NCQQueueManagement abort subcommand
    

class SATAInterpreter:

    def _extract_header(self, HEADER, packet):
        """
            Extract the SATA header and data
            
            @param HEADER: struct format for the SATA header
            @param packet: bytestring of the packet data
            @return: (header, data) where extracted is the struct unpack
        """
        # Calculate teh size of our header
        header_len = struct.Struct(HEADER).size

        # Store our header
        extracted = struct.unpack(HEADER, packet[:header_len])
        
        # Store the remainder as data
        data = packet[header_len:]

        return (extracted, data)

    def extract_sata_data(self, packet):
        """
            Will extract our data data according to 
            SerialATA_Revision_3_0_Gold.pdf
            
            Relevant pages: 383-400ish?
        """

        # # The first word is our header to add semantic information
        # lophi_sata_header = struct.unpack("!I",packet[0:4])[0]
        #
        # direction = lophi_sata_header & 1
        # lophi_seqn = lophi_sata_header >> 16
        #
        # packet = packet[4:]

        # First just extract enough to figure out our message type
        SATA_HEADER_TMP = "!BBBB"
        TMP_SIZE = struct.calcsize(SATA_HEADER_TMP)
#        print packet
        if len(packet) < TMP_SIZE:
            logger.error("SATA packet too small to contain a header!")
            return None
#         tmp = G.flip_endianess(packet[0:TMP_SIZE])
        header_tmp = struct.unpack(SATA_HEADER_TMP, packet[0:TMP_SIZE])

#        print header_tmp
        message_type = header_tmp[3]

        extracted_header = {}
        data = None
        """
            27h    Register FIS - Host to Device
            34h    Register FIS - Device to Host
            39h    DMA Activate FIS - Device to Host
            41h    DMA Setup FIS - Bi-directional
            46h    Data FIS - Bi-directional
            58h    BIST Activate FIS - Bi-directional
            5Fh    PIO Setup FIS - Device to Host
            A1h    Set Device Bits FIS - Device to Host
        """
        # Now look for the packets that we care about

        #
        # 27h    Register FIS - Host to Device (p. 384)
        #
        if message_type == 0x27:
            HEADER = "!BBBB" + "BBH" + "BBH" + "BBH" + "I"

            extracted, data = self._extract_header(HEADER, packet)

            lba1 = extracted[5] << 8 * 2
            lba1 |= extracted[6]

            lba2 = extracted[8] << 8 * 2
            lba2 |= extracted[9]

            lba = (lba2 << 8 * 3) | lba1
            
            #
            # NOTE: NCQ uses features field instead of count field for sector count
            #
            
            extracted_header = {'type':message_type,
                                'features':extracted[0] | extracted[7] << 8,
                                'command':extracted[1],
                                'C':(extracted[2] & 0b10000000) >> 7,
                                'pm_port':extracted[2] & 0b1111,
                                'fis_type':extracted[3],
                                'device':extracted[4],
                                'lba':lba,
                                'control':extracted[10],
                                'icc':extracted[11],
                                'count':extracted[12],
                                'tag': (extracted[12] >> 3) & 0b11111,
                                'direction':direction,
                                'reserved':extracted[13]
                                }


        #
        # 34h    Register FIS - Device to Host
        #
        elif message_type == 0x34:
            HEADER = "!BBBB" + "BBH" + "BBH" + "HH" + "I"
            extracted, data = self._extract_header(HEADER, packet)

            lba1 = extracted[5] << 8 * 2
            lba1 |= extracted[6]

            lba2 = extracted[8] << 8 * 2
            lba2 |= extracted[9]

            lba = (lba2 << 8 * 3) | lba1
            extracted_header = {'type':message_type,
                                'error':extracted[0] ,
                                'status':extracted[1],
                                'interrupt':(extracted[2] & 0b01000000) >> 6,
                                'pm_port':extracted[2] & 0b1111,
                                'fis_type':extracted[3],
                                'device':extracted[4],
                                'lba':lba,
                                'count':extracted[11],
                                'direction':direction,
                                'reserved0':extracted[7],
                                'reserved1':extracted[10],
                                'reserved2':extracted[12]
                                }


        #
        # 41h    DMA Setup FIS - Bi-directional (p. 389)
        #
        elif message_type == 0x41:
            HEADER = "!BBBB" + "I" + "I" + "I" + "I" + "I" + "I"
            extracted, data = self._extract_header(HEADER, packet)

            extracted_header = {'type':message_type,
                                'auto_activate':(extracted[2] & 0b10000000) >> 7,
                                'interrupt':(extracted[2] & 0b1000000) >> 6,
                                'direction_bit':(extracted[2] & 0b100000) >> 5,
                                'direction':direction,
                                'pm_port':extracted[2] & 0b1111,
                                'fis_type':extracted[3],
                                'dma_buf_identifier_low':extracted[4],
                                'dma_buf_identifier_high':extracted[5],
                                'dma_buf_offset':extracted[7],
                                'transfer_count':extracted[8],
                                'reserved0':extracted[6],
                                'reserved1':extracted[9]
                                }

        #
        # 5Fh    PIO Setup FIS - Device to Host (p. 395)
        #
        elif message_type == 0x5f:
            HEADER = "!BBBB" + "BBH" + "BBH" + "BBH" + "HH"
            extracted, data = self._extract_header(HEADER, packet)

            lba1 = extracted[5] << 8 * 2
            lba1 |= extracted[6]

            lba2 = extracted[8] << 8 * 3
            lba2 |= extracted[9]

            lba = (lba2 << 8 * 3) | lba1

            extracted_header = {'type':message_type,
                                'error':extracted[0] ,
                                'status':extracted[1],
                                'direction_bit':(extracted[2] & 0b10000) >> 4,
                                'direction':direction,
                                'pm_port':extracted[2] & 0b1111,
                                'fis_type':extracted[3],
                                'device':extracted[4],
                                'lba':lba,
                                'count':extracted[12],
                                'transfer_count':extracted[14]
                                }


        #
        # 46h    Data FIS - Bi-directional
        #
        elif message_type == 0x46:
            HEADER = "!BBBB"
            extracted, data = self._extract_header(HEADER, packet)

            extracted_header = {'type':message_type,
                                'direction':direction}
        elif message_type == 0x39:
            HEADER = "!HBB"
            extracted, data = self._extract_header(HEADER, packet)
            
            extracted_header = {'pm_port':extracted[1] & 0b1111,
                                'type':message_type,
                                'direction':direction,
                                'reserved':extracted[0]}
        elif message_type == 0xa1:
            HEADER = "!BBBB" + "I"
            extracted, data = self._extract_header(HEADER, packet)
            
            extracted_header = {'error':extracted[0],
                                'status_hi':(extracted[1] & 0b01110000) >> 4,
                                'status_lo':extracted[1] & 0b111,
                                'notification':(extracted[2] & 0b10000000) >> 7,
                                'interrupt':(extracted[2] & 0b01000000) >> 6,
                                'pm_port':extracted[2] & 0b1111,
                                'type':message_type,
                                'direction':direction,
                                'proto':extracted[4]}
        else:
            logger.warn("Got unknown SATA type. (%s)" % hex(message_type))

        # Fix endianess in the data
        if data is not None:
            data = G.flip_endianess(data)
            
        # Add our seqn number that we extracted
#         if extracted_header is not None:
        extracted_header['lophi_seqn'] = lophi_seqn
            
        # return our dicts 
        return (extracted_header, data)



