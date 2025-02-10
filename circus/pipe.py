import os
import io
import socket
from .winpopen import enable_overlapped, disable_overlapped


def make_pipe():
    if os.name != 'nt':
        a, b = os.pipe()
        a, b = io.open(a, 'rb', -1), io.open(b, 'wb', -1)
        return a, b
    else:
        disable_overlapped()
        try:
            serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serv.bind(('127.0.0.1', 0))
            serv.listen(1)

            # need to save sockets in _rsock/_wsock so they don't get closed
            _rsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _rsock.connect(('127.0.0.1', serv.getsockname()[1]))

            _wsock, addr = serv.accept()
            serv.close()
            _rsock_fd = _rsock.makefile('rb', 0)
            _wsock_fd = _wsock.makefile('wb', 0)
            _rsock.close()
            _wsock.close()
            return _rsock_fd, _wsock_fd
        finally:
            enable_overlapped()