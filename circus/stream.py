import fcntl
import errno
import os
import sys
from Queue import Queue


class QueueStream(Queue):
    def __call__(self, data):
        self.put(data)

    def close(self):
        pass


class FileStream(object):
    def __init__(self, filename):
        self._file = open(filename, 'a+')
        self._buffer = []

    def __call__(self, data):
        self._file.write(data['data'])
        self._file.flush()

    def close(self):
        self._file.close()


def get_pipe_redirector(pipe, redirect, extra_info=None, buffer=1024):
    """Redirects data received in pipe to the redirect callable.

    This function creates a Greenlet that continuously reads data
    in the provided pipe and sends it to a callable.

    The data is a mapping with a **data** key containing the data
    received from the pipe, extended with all values passed in
    **extra_info**

    Options:
    - **stream**: the stream to read from
    - **redirect**: the callable to send data to
    - **extra_info**: a mapping of values to add to each call
    - **buffer**: the size of the buffer when reading data
    """
    if extra_info is None:
        extra_info = {}

    try:
        from gevent import Greenlet, socket
    except ImportError:
        raise ImportError('You need to install gevent')

    def _stream(pipe, redirect, extra_info, buffer=1024):
        fcntl.fcntl(pipe, fcntl.F_SETFL, os.O_NONBLOCK)
        fileno = pipe.fileno()

        while True:
            try:
                data = pipe.read(buffer)
                if not data:
                    break
                datamap = {'data': data}
                datamap.update(extra_info)
                redirect(datamap)
            except IOError, ex:
                if ex[0] != errno.EAGAIN:
                    raise
                sys.exc_clear()
            socket.wait_read(fileno)

    return Greenlet(_stream, pipe, redirect, extra_info, buffer)
