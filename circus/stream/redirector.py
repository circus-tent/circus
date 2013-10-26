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
            if events == ioloop.IOLoop.ERROR:
                self.redirector.remove_redirection(self.pipe)
            return
        try:
            data = os.read(fd, self.redirector.buffer)
            if len(data) == 0:
                self.redirector.remove_redirection(self.pipe)
            else:
                datamap = {'data': data, 'pid': self.process.pid,
                           'name': self.name}
                datamap.update(self.redirector.extra_info)
                self.redirector.redirect(datamap)
        except IOError as ex:
            if ex.args[0] != errno.EAGAIN:
                raise
            try:
                sys.exc_clear()
            except Exception:
                pass


class Redirector(object):
    def __init__(self, redirect, extra_info=None,
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
        for fd in list(self._active.keys()):
            self._stop_one(fd)
        self.running = False

    def add_redirection(self, name, process, pipe):
        fd = pipe.fileno()
        self._stop_one(fd)
        self.pipes[fd] = name, process, pipe
        if self.running:
            self._start_one(name, process, pipe)

    def remove_redirection(self, pipe):
        try:
            fd = pipe.fileno()
        except ValueError:
            return
        self._stop_one(fd)
        if fd in self.pipes:
            del self.pipes[fd]
