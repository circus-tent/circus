import fcntl
import errno
import os
import sys


class FileStream(object):
    def __init__(self, filename):
        # how to close that cursor ?
        self._file = open(filename, 'a+')
        self._buffer = []

    def __call__(self, data):
        self._file.write(data['data'])
        self._file.flush()

    def close(self):
        self._file.close()


def get_stream_redirector(pid, output, stream, stream_name):
    try:
        from gevent import Greenlet, socket
    except ImportError:
        raise ImportError('You need to install gevent')


    def _stream(pid, output, stream, stream_name):
        fcntl.fcntl(output, fcntl.F_SETFL, os.O_NONBLOCK)
        fileno = output.fileno()

        while True:
            try:
                data = output.read(1024)
                if not data:
                    break
                stream({'data': data, 'name': stream_name, 'pid': pid})
            except IOError, ex:
                if ex[0] != errno.EAGAIN:
                    raise
                sys.exc_clear()
            socket.wait_read(fileno)

    return Greenlet(_stream, pid, output, stream, stream_name)

