This directory contains a few small scripts and tools that are useful for debugging etc. related to the physical implementation

# Files

	file_creator.py:
		This script is meant to be used on the System Under Analysis to create files of a fixed size filled with A's.  The intution is that you should the output come out through the LO-PHI card.  rapid_debug.py automatically counts A's in the data and reports them to help with debugging.

	send_cmd.py:
		This is used to send arbitrary commands to our Xilinx card. (Ex. python send_cmd.py -o 0x01 -m 0x0000 -l 0 -d "\x00\x00\x00\x03" will turn on SATA extraction)


# Testing Throughput 

  To test the throughput and push the SATA sensor I've created 2 scripts.

	card_test_relay_server.py: 
		This is to be run on the SYSTEM UNDER ANALYSIS, i.e. the system with the FPGA board.  Simply run the script

	card_test_client.py: 
		This is to be run from the development system.  This requires 2 NICS, one that will talk to the FPGA card on 172.20.1.x and one that will connect to the relay server to give instructions on that to write and where.  use --help get more info.


#  Debugging the actual packets 

	rapid_debug.py:
		Will send the wake-up signals too the card and listen forever printing out important context information about the received UDP packets from the LO-PHI card.


# Debugging Your Configuration 

Note that some of the packets being returned may be Jumbo Frames (>1500bytes).  To test and make sure that cards communicating can support jumbo frames trying sending large ping packets.

In Ubuntu type:
	ping -s 1600 <ip address>
Example:

	NO JUMBO FRAMES

	ping -s 1600 172.20.1.100
	PING 172.20.1.100 (172.20.1.100) 1600(1628) bytes of data.
	--- 172.20.1.100 ping statistics ---
	4 packets transmitted, 0 received, 100% packet loss, time 2999ms
	
	JUMBO FRAMES

	ping -s 1600 155.34.26.200
	PING 155.34.26.200 (155.34.26.200) 1600(1628) bytes of data.
	1608 bytes from 155.34.26.200: icmp_req=1 ttl=63 time=1.16 ms
	1608 bytes from 155.34.26.200: icmp_req=2 ttl=63 time=1.17 ms
	1608 bytes from 155.34.26.200: icmp_req=3 ttl=63 time=1.22 ms
	--- 155.34.26.200 ping statistics ---
	3 packets transmitted, 3 received, 0% packet loss, time 2002ms
	rtt min/avg/max/mdev = 1.160/1.184/1.222/0.038 ms

