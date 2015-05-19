#!/usr/bin/python

import socket
import time
import os

UDP_IP = "127.0.0.1"
UDP_PORT = 1664

sock = socket.socket(socket.AF_INET,
                     socket.SOCK_DGRAM)  # UDP

my_pid = os.getpid()

for _ in range(25):
    message = "{pid};{time}".format(pid=my_pid, time=time.time())
    print('sending:{0}'.format(message))
    sock.sendto(message, (UDP_IP, UDP_PORT))
    time.sleep(2)
