"""
    Generally useful utilities

    (c) 2015 Massachusetts Institute of Technology
"""
class stack(list):
    
    sector_dict = {}
    head = -1
    
    def __contains__(self, sector):
        """
            See if we already have an element with that LBA/sector
            
            @param sector: Sector of packet in queue
            @return: True if an element with that index exists, false otherwise. 
        """
        if sector in self.sector_dict.keys():
            return True
        else:
            return False
        
        
    def get(self, sector):
        """
            Return an element based on it's sector
            
            @param sector: Index of element to return
            @return: Element requested or None  
        """
        if sector in self.sector_dict.keys():
            return self.sector_dict[sector]
        else:
            return None
    
        
    def update_head(self, sector):
        """
            Update the head of our stack to the element with the given sector.
            
            @param sector: Index of element to now set as the head. 
            @return: True if element exists, False otherwise
        """
        if sector in self.sector_dict.keys():
            self.head = self.index(self.sector_dict[sector])
            return True
        else:
            return False
    
    
    def push(self, item):
        """
            Pushes a disk sensor packet to our stack and also does some book keeping.
            
            @param item: Disk sensor packet (w/ .sector attribute) 
        """
        self.append(item)
        self.sector_dict[item.sector] = item 
        
        self.head = -1
        
        
    def pop(self):
        """
            Return the current head of the stack and remove it
            
            @return: Current element pointed to by head or None
        """
        if self.is_empty():
            return None
        
        # Get our element from the head
        rtn = self[self.head]
        
        # Remove item from our list and dictionary
        self.remove(rtn)
        del self.sector_dict[rtn.sector]
        
        self.head = -1
        
        return rtn
        
        
    def peek(self):
        """
            Peek at the current head
            
            @return: Current head or None
        """
        
        if self.is_empty():
            return None
        else:
            return self[self.head]
        
    
    def is_empty(self):
        
        return not self

# Watchdog timer from: http://www.dzone.com/snippets/simple-python-watchdog-timer
import signal

class Watchdog(Exception):
    def __init__(self, time=5):
        self.time = time
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(self.time)
        
    def __exit__(self, t, value, traceback):
        signal.alarm(0)
    
    def handler(self, signum, frame):
        raise self
    
    def __str__(self):
        return "The code you executed took more than %ds to complete" % self.time