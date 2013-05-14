import fcntl
import errno
import os
import sys

from zmq.eventloop import ioloop

class Redirector(object):
    def __init__(self, redirect, refresh_time=1.0, extra_info=None,
                 buffer=1024, loop=None):
        self.pipes = []
        self._names = {}
        self.redirect = redirect
        self.extra_info = extra_info
        self.buffer = buffer
        if extra_info is None:
            extra_info = {}
        self.extra_info = extra_info
        self.loop = loop or ioloop.IOLoop.instance()

    def start(self):
        pass

    def kill(self):
        for key, pipe in self._names.items():
            self.loop.remove_handler(pipe.fileno())
            del self._names[key]

    def add_redirection(self, name, process, pipe):
        def _handler(fd, events):
            if not (events & self.loop.READ):
                return
            try:
                data = os.read(fd, self.buffer)
                if len(data) == 0:
                    self.remove_redirection(name, process)
                else:
                    datamap = {'data': data, 'pid': process.pid,
                               'name': name}
                    datamap.update(self.extra_info)
                    self.redirect(datamap)
            except IOError, ex:
                if ex[0] != errno.EAGAIN:
                    raise
                sys.exc_clear()

        self.loop.add_handler(pipe.fileno(), _handler, self.loop.READ)
        self._names[process.pid, name] = pipe

    def remove_redirection(self, name, process):
        key = process.pid, name
        if key not in self._names:
            return
        pipe = self._names[key]
        self.loop.remove_handler(pipe.fileno())
        del self._names[key]

