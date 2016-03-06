"""
    Abstract class for interacting with our memory sensors

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import time
import logging

logger = logging.getLogger(__name__)

# LO-PHI
from lophi.sensors import Sensor

CACHE_CHUNK = 7680  # 7680 is the max


class MemorySensor(Sensor):
    """"
        This is an abstract class to help manage both physical and virtual
        implementations.  This will also allow us to expand to new 
        implementations very easily.
    """

    # Format: [START,END)
    BAD_MEM_REGIONS = []

    def __init__(self):
        """ Initialize our class """

        # Ensure that this class is never initialized directly
        if self.__class__ == MemorySensor:
            raise ("Interface initialized directly!")

        Sensor.__init__(self)

    def _read_from_sensor(self, address, length):
        """ Read memory from the sensor directly """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def _read_cached(self, address, length):
        """
            Read memory from the sensor, caching values if enabled.
            
            @param address: Starting physical memory address
            @param length: Length of memory to read
            @return: RAW data string from memory 
            
            @todo: CLEAN UP THE CACHE!
        """

        # Is the cache disabled?
        if self.CACHE_TIMEOUT <= 0:
            rtn = self._read_from_sensor(address, length)
            if rtn is None:
                return ""
            else:
                return rtn

        # Temp variable for cached data
        datas = ""
        NOW = time.time()

        # Loop over each chunk in the cache
        while (length > 0):

            cacheindex = address / CACHE_CHUNK
            chunkstart = cacheindex * CACHE_CHUNK
            cacheoffset = address - chunkstart
            inchunk = CACHE_CHUNK - cacheoffset

            # See if we have a cached version, and if its expired
            if cacheindex not in self.cache or self.cache_timeouts[
                cacheindex] <= NOW - self.CACHE_TIMEOUT:

                # Read the memory from our sensor
                entry = self._read_from_sensor(chunkstart, CACHE_CHUNK)
                if entry is None:
                    logger.error("Problem reading from sensor!")
                    return datas

                # Cache this entry
                self.cache[cacheindex] = entry
                # Save the time that we got this entry
                self.cache_timeouts[cacheindex] = NOW

            # Only append what was requested
            if length > CACHE_CHUNK - cacheoffset:
                datas += self.cache[cacheindex][cacheoffset:]
            else:
                datas += self.cache[cacheindex][
                         cacheoffset:cacheoffset + length]

            address += inchunk
            length -= inchunk

        return datas

    def read(self, address, length):
        """
            Read memory from our sensor
            
            NOTE: This will use our temporal cache if it's set and handle any 
            memory holes
            
            @param address: Starting physical memory address
            @param length: Length of memory to read
            @return: RAW data string from memory 
        """

        logger.debug("Got read (0x%x,%d)" % (address, length))

        READS = []

        # Given a read like below, we'll want to read the - sections and fill in
        # zeros for the * sections where
        #
        # S--------b1s***b1e-----b2s***b2e------E
        #
        # S - address, E - address+length, bX(s/e) - bad region start/end
        #
        # NOTE: BAD_MEM_REGIONS is assumed to be sorted!
        # There are also faster ways to do this, but this is already likely a 
        # rare case to have many bad regions
        last_bad = None
        for bad in self.BAD_MEM_REGIONS:

            # Does the entire requested region fall in a bad sector?
            if bad[0] <= address and bad[1] >= address + length:
                logger.debug(
                    "Entire region is in bad memory %s, returning 0s" % str(
                        bad))
                return "\x00" * length

            # Does this region start within our read?
            if bad[0] >= address and bad[0] < address + length:

                logger.debug("Region starts in bad memory. %s" % str(bad))
                # We'll need to do one read from the start of the previous bad 
                # region to the beginning of this bad region
                if last_bad is None and address != bad[0]:
                    READS.append((address, bad[0]))
                elif last_bad is not None:
                    READS.append((last_bad[1], bad[0]))

                last_bad = bad

            # Does this read request start in a bad region?
            elif bad[1] > address and bad[1] < address + length:
                last_bad = bad

            # Are we oustide of the region that we are worried about?
            elif bad[0] > address + length:
                continue

        # Are we doing multiple reads?
        if len(READS) > 0 or last_bad is not None:
            # Do we need a final read to pick up the left over case?
            # i.e. b2e------E
            if last_bad[1] < address + length:
                READS.append((last_bad[1], address + length))

            # variable to store our data
            data = ""

            # Do we need to prepend zeros?
            if READS[0][0] > address:
                data += "\x00" * (READS[0][0] - address)

            logger.debug("Issuing the following reads: %s" % READS)

            last_read = None
            for read in READS:
                # Append any zeros for the bad sections
                # ..--b1s***b1e--..
                # bs1 = last_read[1], bs1e = read[0]
                if last_read is not None:
                    data += "\x00" * (read[0] - last_read[1])

                read_data = self._read_cached(read[0], read[1] - read[0])

                if read_data is None or len(read_data) == 0:
                    logger.error("Got no data back from sensor.  (Timeout)")
                    return None

                data += read_data

                last_read = read

            # Do we need to append zero's to the end to hit our length?
            if len(data) < length:
                data += "\x00" * (length - len(data))

            return data

        else:
            return self._read_cached(address, length)

    def write(self, address, data):
        """ Write memory """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def subscribe(self):
        """ Subscribe to a memory region """
        raise NotImplementedError("ERROR: Unimplemented function.")

    def unsubscribe(self):
        """ Un-subscribe from a memory region """
        raise NotImplementedError("ERROR: Unimplemented function.")
