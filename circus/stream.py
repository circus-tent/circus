import fcntl
import errno
import os
import sys
from Queue import Queue
from threading import Thread
import select
import time


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


class NamedPipe(object):
    def __init__(self, pipe, process, name):
        self.pipe = pipe
        self.process = process
        self.name = name
        fcntl.fcntl(pipe, fcntl.F_SETFL, os.O_NONBLOCK)
        self._fileno = pipe.fileno()

    def fileno(self):
        return self._fileno

    def read(self, buffer):
        if self.pipe.closed:
            return
        return self.pipe.read(buffer)


class BaseRedirector(object):
    def __init__(self, redirect, extra_info=None, buffer=1024, selector=None):
        self.pipes = []
        self._names = {}
        self.redirect = redirect
        self.extra_info = extra_info
        self.buffer = buffer
        self.running = False
        if extra_info is None:
            extra_info = {}
        self.extra_info = extra_info
        if selector is None:
            selector = select.select
        self.selector = selector

    def add_redirection(self, name, process, pipe):
        npipe = NamedPipe(pipe, process, name)
        self.pipes.append(npipe)
        self._names[process.pid, name] = npipe

    def remove_redirection(self, name, process):
        pipe = self._names[process.pid, name]
        self.pipes.remove(pipe)
        del self._names[process.pid, name]

    def _select(self):
        if len(self.pipes) == 0:
            time.sleep(.1)
            return

        try:
            try:
                rlist, __, __ = self.selector(self.pipes, [], [])
            except select.error:     # need a non specific error
                return

            for pipe in rlist:
                data = pipe.read(self.buffer)
                if data:
                    datamap = {'data': data, 'pid': pipe.process.pid,
                                'name': pipe.name}
                    datamap.update(self.extra_info)
                    self.redirect(datamap)
        except IOError, ex:
            if ex[0] != errno.EAGAIN:
                raise
            sys.exc_clear()

# if gevent and gevent_zmq are available, let's use a Greenlet
# o/wise fallback to a Thread + a select
try:
    import gevent_zeromq    # just to make sure zmq will not block  # NOQA
    from gevent import Greenlet
    from gevent.select import select as gselect

    class GreenRedirector(BaseRedirector, Greenlet):
        def __init__(self, redirect, extra_info=None, buffer=1024):
            Greenlet.__init__(self)
            BaseRedirector.__init__(self, redirect, extra_info, buffer,
                                    selector=gselect)

        def _run(self, *args, **kwargs):
            while True:
                self._select()

    Redirector = GreenRedirector
except ImportError:

    class ThreadedRedirector(BaseRedirector, Thread):
        def __init__(self, redirect, extra_info=None, buffer=1024):
            Thread.__init__(self)
            BaseRedirector.__init__(self, redirect, extra_info, buffer)
            self.running = False

        def run(self):
            self.running = True

            while self.running:
                self._select()

        def kill(self):
            if not self.running:
                return
            self.running = False
            self.join()

    Redirector = ThreadedRedirector


def get_pipe_redirector(redirect, extra_info=None, buffer=1024):
    """Redirects data received in pipes to the redirect callable.

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
    - **redirect**: the callable to send data to
    - **extra_info**: a mapping of values to add to each call
    - **buffer**: the size of the buffer when reading data
    """
    return Redirector(redirect, extra_info, buffer)
