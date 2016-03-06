#!/usr/bin/python

#*****************************************************************
# Copyright 2010 MIT Lincoln Laboratory  
# Project:           LO-PHI
# Author:            Joshua Hodosh
# Description:       CLI client interface for LO-PHI NIC protocol
#*****************************************************************


import socket
import sys
import string
import binascii
import threading
import optparse
from struct import *
from collections import deque

MEMORY_HOLE_START = 1024*640
MEMORY_HOLE_END   = 1024*1024
MEMORY_HOLE_LEN   = MEMORY_HOLE_END - MEMORY_HOLE_START

CACHE_CHUNK = 768

# things that are from lophi.h
MAGIC_HEX = 0xDEADBEEF
DEFAULT_NODE = 0x00000000
DEFAULT_FLAGS = 0x00000000
PORT_NO = 31337
LOPHI_COMMAND_PING    = 10
LOPHI_COMMAND_READ    = 0
LOPHI_COMMAND_WRITE   = 2
LOPHI_COMMAND_SUB     = 3
LOPHI_COMMAND_UNSUB   = 4
LOPHI_COMMAND_LIST    = 5
LOPHI_UPDATE_NOTICE   = 6
LOPHI_COMMAND_SEARCH  = 7
LOPHI_COMMAND_DEBUG   = 253
LOPHI_COMMAND_LOG     = 254
LOPHI_COMMAND_VERSION = 255

LOPHI_PING_SIZE      = 9
LOPHI_READ_REQ_LEN   = 26
#LOPHI_READ_RESP_LEN  = 15
LOPHI_READ_RESP_LEN  = 28
LOPHI_WRITE_RESP_LEN = 8
LOPHI_SUB_RESP_LEN   = 10
LOPHI_SUB_NOTIFY_LEN = 27
LOPHI_VER_RESP_LEN   = 13

LOPHI_SUB_ERROR_FULL  = 1
LOPHI_SUB_ERROR_RANGE =2
LOPHI_SUB_ERROR_HOLE  = 3
LOPHI_UNSUB_ERROR_NOT_FOUND = 1
LOPHI_UNSUB_ERROR_GONE    =  2

# End things from lophi.h

def main():
    args=sys.argv[1:]
    usage = "usage: %prog [options]"
    opts = optparse.OptionParser(usage=usage)
    opts.add_option("-j",help="Jumbo ping",action='store_true', default=False,
                    dest="jumbo")
    opts.add_option("-t","--target",help="IP of target device. Defaults to %default",action='store', default='172.20.1.1',
                    dest="ip")
    opts.add_option("-p","--payload",help="Contents of ping. Defaults to empty",action='store',default='',
                    dest='payload')
    opts.add_option("-c", "--count", help="Number of pings to send", action='store', default=1, type="int",
                    dest='count')
    (options, positionals) = opts.parse_args(args)
    client = LOPHI_Client(options.ip)
    
    for i in range(options.count):
        if options.jumbo:
            client.ping_new()
        else:
            client.ping(options.payload)

def hex2char(hexString,  length):
    string_list = []
    for i in range(0,  len(hexString), 2):
        string_list.append(binascii.unhexlify(hexString[i:i+2]))

    if(length > 0):
        while (len(string_list) < length):
            string_list.insert(0, binascii.unhexlify('00'))

    return "".join(string_list)
    
def ascii2hex(ascii):
    string_list = []
    for i in range(0,  len(ascii)):
        string_list.append(binascii.hexlify(ascii[i]))
    return "".join(string_list)
    
def zeros(length):   
    string_list = []
    zero = binascii.unhexlify('00')
    while(len(string_list) < length):
        string_list.append(zero)
    return "".join(string_list)

class LOPHI_Client:
    def __init__(self, ip):
        self.sensor_ip = ip
        self.transaction_no = 1
        self.live_subscriptions = set()
        self.socket = None
        self.cache = {}
        self.cacheorder = deque()

    def openSocket(self):
        if self.socket is None:
            s = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 100000)
            s.connect((self.sensor_ip, PORT_NO))
            self.socket = s
        return self.socket
    
    def menu(self):
        print "Commands: \n"
        print "0: Ping"
        print "1: Jumbo Ping\n"
        choice = int(input("Select command (-1 to exit): "))
        if(choice == 0):
            self.ping()
        elif(choice == 1):
            self.ping_new()
        elif(choice == 2):
            self.write()

        elif(choice == -1):
            if(len(self.live_subscriptions) >0):
                print "There are still subscriptions for this machine. Refusing to exit"
            else:
                sys.exit(0)
        else:
            print "unrecognized choice\n"
        self.transaction_no+=1
        self.menu()

# RAPID - change port to 31338
    def ping(self, message=None):
        s = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
        if message is None:
            message = raw_input("Enter ping data: ")

        print "Ping data length is %d" %  len(message)
        s.connect((self.sensor_ip, PORT_NO + 1))
        payload = pack('!IHBH', MAGIC_HEX,  self.transaction_no, LOPHI_COMMAND_PING, len(message)) + message
        s.send(payload)
        data = s.recv(9000)
        if(data[9:]  == message):
            print "Ping!"
        else:
            print "receieved \" "  +data+ " \""
        s.close()

    def ping_new(self):
        s = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
        message = 'kalfjewiofjoiw2jfijf8u92jf9iu34h4yrf87urehf873hf9u8324hf9uh4f9fj398fju9234jfiowfjwuvh34uvjn93u4jviowrevriofj3ijf3948icmji934jc0i23jciwe4j3f9wj c9ifj439fj9843jfc934jci43j9icj4239 0422xoij892icx jk42389jc i24jdi023jd9ij3jd i23j dio23j  9idj 1398dk 213id2i di29dji923jd9823jcxji9234jfciu23h4f8udciuej28fuweju9ifhweiuchf38uweijcf3uwiejc98woiejmec9wiuoejfcwioejfmciowehfndcio243hjewimfojmewio fhcneomwkjjf hnoei hfcnioqeq whfcnoif24e whjnj9ufikewjfu9iewok fhcnewoif hcjmqwoetyhfwjscoim34yhweuioaslkddh4ewiomksdlfy8u9iewjfiewojkmdscfewroivksdngvkd clvkdasndokgfjf324iujfiovdsajrt98jiorjgweqioAJOIJGRIAJGOIJREUI9TJIOJ8irewjqtiahjoifgJAGJIOEQUAGIORSJHT98UGJWEoitje8w9iarjgioewrjgoif35j89ewjg834wjv9ug35hnivu5h4e rt7jh&He7894h*&89UFUWHEUIFHWEUFHUWEHFUWHUWHF834HF874H8FHHHHJSHFG'+ \
        'kalfjewiofjoiw2jfijf8u92jf9iu34h4yrf87urehf873hf9u8324hf9uh4f9fj398fju9234jfiowfjwuvh34uvjn93u4jviowrevriofj3ijf3948icmji934jc0i23jciwe4j3f9wj c9ifj439fj9843jfc934jci43j9icj4239 0422xoij892icx jk42389jc i24jdi023jd9ij3jd i23j dio23j  9idj 1398dk 213id2i di29dji923jd9823jcxji9234jfciu23h4f8udciuej28fuweju9ifhweiuchf38uweijcf3uwiejc98woiejmec9wiuoejfcwioejfmciowehfndcio243hjewimfojmewio fhcneomwkjjf hnoei hfcnioqeq whfcnoif24e whjnj9ufikewjfu9iewok fhcnewoif hcjmqwoetyhfwjscoim34yhweuioaslkddh4ewiomksdlfy8u9iewjfiewojkmdscfewroivksdngvkd clvkdasndokgfjf324iujfiovdsajrt98jiorjgweqioAJOIJGRIAJGOIJREUI9TJIOJ8irewjqtiahjoifgJAGJIOEQUAGIORSJHT98UGJWEoitje8w9iarjgioewrjgoif35j89ewjg834wjv9ug35hnivu5h4e rt7jh&He7894h*&89UFUWHEUIFHWEUFHUWEHFUWHUWHF834HF874H8FHHHHJSHFG'+\
        'kalfjewiofjoiw2jfijf8u92jf9iu34h4yrf87urehf873hf9u8324hf9uh4f9fj398fju9234jfiowfjwuvh34uvjn93u4jviowrevriofj3ijf3948icmji934jc0i23jciwe4j3f9wj c9ifj439fj9843jfc934jci43j9icj4239 0422xoij892icx jk42389jc i24jdi023jd9ij3jd i23j dio23j  9idj 1398dk 213id2i di29dji923jd9823jcxji9234jfciu23h4f8udciuej28fuweju9ifhweiuchf38uweijcf3uwiejc98woiejmec9wiuoejfcwioejfmciowehfndcio243hjewimfojmewio fhcneomwkjjf hnoei hfcnioqeq whfcnoif24e whjnj9ufikewjfu9iewok fhcnewoif hcjmqwoetyhfwjscoim34yhweuioaslkddh4ewiomksdlfy8u9iewjfiewojkmdscfewroivksdngvkd clvkdasndokgfjf324iujfiovdsajrt98jiorjgweqioAJOIJGRIAJGOIJREUI9TJIOJ8irewjqtiahjoifgJAGJIOEQUAGIORSJHT98UGJWEoitje8w9iarjgioewrjgoif35j89ewjg834wjv9ug35hnivu5h4e rt7jh&He7894h*&89UFUWHEUIFHWEUFHUWEHFUWHUWHF834HF874H8FHHHHJSHFG'+\
        'kalfjewiofjoiw2jfijf8u92jf9iu34h4yrf87urehf873hf9u8324hf9uh4f9fj398fju9234jfiowfjwuvh34uvjn93u4jviowrevriofj3ijf3948icmji934jc0i23jciwe4j3f9wj c9ifj439fj9843jfc934jci43j9icj4239 0422xoij892icx jk42389jc i24jdi023jd9ij3jd i23j dio23j  9idj 1398dk 213id2i di29dji923jd9823jcxji9234jfciu23h4f8udciuej28fuweju9ifhweiuchf38uweijcf3uwiejc98woiejmec9wiuoejfcwioejfmciowehfndcio243hjewimfojmewio fhcneomwkjjf hnoei hfcnioqeq whfcnoif24e whjnj9ufikewjfu9iewok fhcnewoif hcjmqwoetyhfwjscoim34yhweuioaslkddh4ewiomksdlfy8u9iewjfiewojkmdscfewroivksdngvkd clvkdasndokgfjf324iujfiovdsajrt98jiorjgweqioAJOIJGRIAJGOIJREUI9TJIOJ8irewjqtiahjoifgJAGJIOEQUAGIORSJHT98UGJWEoitje8w9iarjgioewrjgoif35j89ewjg834wjv9ug35hnivu5h4e rt7jh&He7894h*&89UFUWHEUIFHWEUFHUWEHFUWHUWHF834HF874H8FHHHHJSHFG'
        print "Ping data length is %d" % len(message)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 100000)
        s.connect((self.sensor_ip, PORT_NO + 1))
        payload = pack('!IHBH', MAGIC_HEX,  self.transaction_no, LOPHI_COMMAND_PING, len(message)) + message
        s.send(payload)
        data = s.recv(8192)
        if(data[9:]  == message):
            print "Ping!"
        else:
            print "receieved \" "  +data+ " \""
            print len(data)
        s.close()

    def change_IP(self):
        self.set_IP(raw_input("Enter new target IP: "))
    
    def set_IP(self, new_IP):
        global ip_address
        self.sensor_ip = new_IP

if __name__ == "__main__":
    main()
