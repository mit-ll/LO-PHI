#!/usr/bin/env python
 
"""
A pure Python "ping" implementation, based on a rewrite by Johannes Meyer,
of a script originally by Matthew Dixon Cowles. Which in turn was derived
from "ping.c", distributed in Linux's netkit. The version this was forked
out of can be found here: https://gist.github.com/pklaus/856268
 
I've rewritten nearly everything for enhanced performance and readability,
and removed unnecessary functions (assynchroneous PingQuery and related).
Those of the original comments who still applied to this script were kept.
 
A lot was changed on my rewrite, and as far as my tests went it is working
quite beautifully. In any case, bug reports are very much welcome.
 
Please note that ICMP messages can only be sent by processes ran as root.
 
Since this was originally based on "ping.c", which a long, long time ago
was released under public domain. I will follow the Open Source mindset
and waive all rights over this script. Do whatever you want with it, just
don't hold me liable for any losses or damages that could somehow come
out of a freaking "ping" script.
 
Cheers and enjoy!
 
"""
 
import socket
import struct
import select
import random
from time import time
 
ICMP_ECHO_REQUEST = 8
ICMP_CODE = socket.getprotobyname('icmp')
ERROR_DESCR = {
    1: 'ERROR: ICMP messages can only be sent from processes running as root.',
    10013: 'ERROR: ICMP messages can only be sent by users or processes with administrator rights.'
    }
__all__ = ['create_packet', 'echo', 'recursive']
 
 
def checksum(source_string):
    sum = 0
    count_to = (len(source_string) / 2) * 2
    count = 0
    while count < count_to:
        this_val = ord(source_string[count + 1])*256+ord(source_string[count])
        sum = sum + this_val
        sum = sum & 0xffffffff  # Necessary?
        count = count + 2
    if count_to < len(source_string):
        sum = sum + ord(source_string[len(source_string) - 1])
        sum = sum & 0xffffffff  # Necessary?
    sum = (sum >> 16) + (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xffff
 
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer
 
 
def create_packet(id):
    """Creates a new echo request packet based on the given "id"."""
    # Builds Dummy Header
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, 0, id, 1)
    data = 192 * 'Q'
 
    # Builds Real Header
    header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, socket.htons(checksum(header + data)), id, 1)
    return header + data
 
 
def response_handler(sock, packet_id, time_sent, timeout):
    """Handles packet response, returning either the delay or timing out (returns "None")."""
    while True:
        ready = select.select([sock], [], [], timeout)
        if ready[0] == []:  # Timeout
            return
 
        time_received = time()
        rec_packet, addr = sock.recvfrom(1024)
        icmp_header = rec_packet[20:28]
        type, code, checksum, rec_id, sequence = struct.unpack('bbHHh', icmp_header)
 
        if rec_id == packet_id:
            return time_received - time_sent
 
        timeout -= time_received - time_sent
        if timeout <= 0:
            return
 
 
def echo(dest_addr, timeout=1):
    """
    Sends one ICMP packet to the given destination address (dest_addr)
    which can be either an ip or a hostname.
 
    "timeout" can be any integer or float except for negatives and zero.
 
    Returns either the delay (in seconds), or "None" on timeout or an
    invalid address, respectively.
 
    """
 
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_CODE)
    except socket.error, (error_number, msg):
        if error_number in ERROR_DESCR:
            # Operation not permitted
            raise socket.error(''.join((msg, ERROR_DESCR[error_number])))
        raise  # Raises the original error
 
    try:
        socket.gethostbyname(dest_addr)
    except socket.gaierror:
        return
 
    packet_id = int((id(timeout) * random.random()) % 65535)
    packet = create_packet(packet_id)
    while packet:
        # The icmp protocol does not use a port, but the function
        # below expects it, so we just give it a dummy port.
        sent = sock.sendto(packet, (dest_addr, 1))
        packet = packet[sent:]
 
    delay = response_handler(sock, packet_id, time(), timeout)
    sock.close()
    return delay
 
 
def recursive(dest_addr, count=4, timeout=1, verbose=False):
    """
    Pings "dest_addr" "count" times and returns a list of replies. If
    "verbose" is True prints live feedback.
 
    "count" can be any integer larger than 0.
    "timeout" can be any integer or float except for negatives and zero.
 
    Returns a list of delay times for the response (in seconds). If no
    response is recorded "None" is stored.
 
    """
 
    if verbose:
        print("PING {} ; SEQUENCE {} ; TIMEOUT {}s".format(dest_addr, count, timeout))
        nrc = 0
 
    log = []
    for i in xrange(count):
        log.append(echo(dest_addr, timeout))
        if verbose:
            if log[-1] is None:
                print("Echo Request Failed...")
                nrc += 1
            else:
                print("Echo Received:  sequence_id={}  delay={} ms").format(i, round(log[-1]*1000, 3))
 
    # Code block below is malfunctioning, it's late and I'm too damn tired to fix it. Maybe tomorrow.
    # if verbose:
    #     print("PACKET STATISTICS: sent={} received={} ratio={}%".format(count, count-nrc, (count-nrc * 100)/count))
    #     print("max/min/avg in ms  {}/{}/{}".format(max(log), min(log), round(sum([x*1000 for x in log if x is not None])/len(log), 3)))
 
    return log
 
 
# Testing
if __name__ == '__main__':
    recursive('127.0.0.1', 4, 2, True)
