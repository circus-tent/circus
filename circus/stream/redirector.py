import errno
import os
import sys

from zmq.eventloop import ioloop


class RedirectorHandler(object):
    def __init__(self, redirector, name, process, pipe):
        self.redirector = redirector
        self.name = name
        self.process = process
        self.pipe = pipe

    def __call__(self, fd, events):
        if not (events & ioloop.IOLoop.READ):
            return
        try:
            data = os.read(fd, self.redirector.buffer)
            if len(data) == 0:
                self.redirector.remove_redirection(self.name, self.process)
            else:
                datamap = {'data': data, 'pid': self.process.pid,
                           'name': self.name}
                datamap.update(self.redirector.extra_info)
                self.redirector.redirect(datamap)
        except IOError, ex:
            if ex[0] != errno.EAGAIN:
                raise
            sys.exc_clear()


class Redirector(object):
    def __init__(self, redirect, refresh_time=1.0, extra_info=None,
                 buffer=4096, loop=None):
        self.running = False
        self.pipes = {}
        self._active = {}
        self.redirect = redirect
        self.extra_info = extra_info
        self.buffer = buffer
        if extra_info is None:
            extra_info = {}
        self.extra_info = extra_info
        self.loop = loop or ioloop.IOLoop.instance()

    def _start_one(self, name, process, pipe):
        fd = pipe.fileno()
        if fd not in self._active:
            handler = RedirectorHandler(self, name, process, pipe)
            self.loop.add_handler(fd, handler, ioloop.IOLoop.READ)
            self._active[fd] = handler

    def start(self):
        for name, process, pipe in self.pipes.values():
            self._start_one(name, process, pipe)
        self.running = True

    def _stop_one(self, fd):
        if fd in self._active:
            self.loop.remove_handler(fd)
            del self._active[fd]

    def stop(self):
        for fd in self._active.keys():
            self._stop_one(fd)
        self.running = False

    def add_redirection(self, name, process, pipe):
        fd = pipe.fileno()
        self._stop_one(fd)
        self.pipes[fd] = name, process, pipe
        if self.running:
            self._start_one(name, process, pipe)

    def remove_redirection(self, pipe):
        fd = pipe.fileno()
        self._stop_one(fd)
        if fd in self.pipes:
            del self.pipes[fd]
