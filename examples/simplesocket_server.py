import socket
import sys
import time
import os
import random

fd = int(sys.argv[1])   # getting the FD from circus
sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)

# By default socket created by circus is in non-blocking mode. For this example
# we change this.
sock.setblocking(1)
random.seed()

while True:
    conn, addr = sock.accept()
    conn.sendall("Hello Circus by %s" % (os.getpid(),))
    seconds = random.randint(2, 12)
    time.sleep(seconds)
    conn.close()
