import fcntl
import errno
import os
import sys

from zmq.eventloop import ioloop


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


class Redirector(object):
    def __init__(self, redirect, refresh_time=1.0, extra_info=None,
                 buffer=1024, loop=None):
        self.pipes = []
        self._names = {}
        self.redirect = redirect
        self.extra_info = extra_info
        self.buffer = buffer
        self.running = False
        if extra_info is None:
            extra_info = {}
        self.extra_info = extra_info
        self.refresh_time = refresh_time * 1000
        self.loop = loop or ioloop.IOLoop.instance()
        self.caller = None

    def start(self):
        self.caller = ioloop.PeriodicCallback(self._select, self.refresh_time,
                                              self.loop)
        self.caller.start()

    def kill(self):
        if self.caller is None:
            return
        self.caller.stop()

    def add_redirection(self, name, process, pipe):
        npipe = NamedPipe(pipe, process, name)
        self.pipes.append(npipe)
        self._names[process.pid, name] = npipe

    def remove_redirection(self, name, process):
        key = process.pid, name
        if key not in self._names:
            return
        pipe = self._names[key]
        self.pipes.remove(pipe)
        del self._names[key]

    def _select(self):
        if len(self.pipes) == 0:
            return

        # we just try to read, if we see some data
        # we just redirect it.
        try:
            for pipe in self.pipes:
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
