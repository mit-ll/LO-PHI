"""
	Script used to parse all of the ports from Wikipedia
"""
from lophi_semanticgap.network import PORTS

tcp = {}
udp = {}
for line in PORTS.split('\n'):
    if len(line) == 0:
        continue
    lines = line.split()
    
    port = int(lines[0])
    
    is_tcp = False
    is_udp = False
    official = None
    description = None
    
    if lines[1] == "TCP":
        is_tcp = True
        if lines[2] == "UDP":
            is_udp = True
            description = ' '.join(lines[3:-1])
        else:
            description = ' '.join(lines[2:-1])
            
    elif lines[1] == "UDP":
        is_udp = True
        description = ' '.join(lines[2:-1])
    else:
        is_udp = is_tcp = True
        description = ' '.join(lines[1:-1])
        
    official = lines[-1]
    
    
        
    entry = description
    
    if is_tcp:
        tcp[port] = entry
    if is_udp:
        udp[port] = entry
        
    
print "UDP_PORTS = ",udp
print "TCP_PORTS = ",tcp
