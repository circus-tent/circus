import socket

#connect to a worker
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 8888))

data = sock.recv(100)
print 'Received : ', repr(data)
sock.close()
