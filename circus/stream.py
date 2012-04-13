import fcntl
import errno
import os
import sys
from Queue import Queue
from threading import Thread
import select


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


# if gevent and gevent_zmq are available, let's use a Greenlet
# o/wise fallback to a Thread + a select
try:
    import gevent_zeromq    # just to make sure zmq will not block  # NOQA
    from gevent import Greenlet, socket

    class GreenRedirector(Greenlet):
        def __init__(self, pipe, redirect, extra_info=None, buffer=1024):
            Greenlet.__init__(self)
            fcntl.fcntl(pipe, fcntl.F_SETFL, os.O_NONBLOCK)
            self.pipe = pipe
            self.redirect = redirect
            self.extra_info = extra_info
            self.buffer = buffer
            self.running = False
            self.fileno = pipe.fileno()
            if extra_info is None:
                extra_info = {}
            self.extra_info = extra_info

        def _run(self, *args, **kwargs):
            while True:
                try:
                    data = self.pipe.read(self.buffer)
                    if not data:
                        break
                    datamap = {'data': data}
                    datamap.update(self.extra_info)
                    self.redirect(datamap)
                except IOError, ex:
                    if ex[0] != errno.EAGAIN:
                        raise
                    sys.exc_clear()
                socket.wait_read(self.fileno)

    Redirector = GreenRedirector
except ImportError:

    class ThreadedRedirector(Thread):
        def __init__(self, pipe, redirect, extra_info=None, buffer=1024):
            Thread.__init__(self)
            fcntl.fcntl(pipe, fcntl.F_SETFL, os.O_NONBLOCK)
            self.pipe = pipe
            self.redirect = redirect
            self.extra_info = extra_info
            self.buffer = buffer
            self.running = False
            if extra_info is None:
                extra_info = {}
            self.extra_info = extra_info

        def run(self):
            self.running = True
            while self.running:
                try:
                    data = self.pipe.read(self.buffer)
                    if not data:
                        break
                    datamap = {'data': data}
                    datamap.update(self.extra_info)
                    self.redirect(datamap)
                except IOError, ex:
                    if ex[0] != errno.EAGAIN:
                        raise
                    sys.exc_clear()

                select.select([self.pipe], [], [self.pipe])

        def kill(self):
            self.running = False
            self.join()

    Redirector = ThreadedRedirector


def get_pipe_redirector(pipe, redirect, extra_info=None, buffer=1024):
    """Redirects data received in pipe to the redirect callable.

    This function creates a separate thread that continuously reads
    data in the provided pipe and sends it to the provided callable.

    If Gevent and Gevent_zeromq are installed, this function will use
    a Greenlet for efficiency. It will fallback to a plain thread otherwise,
    and that may lead to poor performances and a lot of memory consumption
    when you have a lot of workers.

    The data is a mapping with a **data** key containing the data
    received from the pipe, extended with all values passed in
    **extra_info**

    Options:
    - **stream**: the stream to read from
    - **redirect**: the callable to send data to
    - **extra_info**: a mapping of values to add to each call
    - **buffer**: the size of the buffer when reading data
    """
    return Redirector(pipe, redirect, extra_info, buffer)
