import fcntl
import errno
import os
import select
import sys
import time


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
    def __init__(self, redirect, refresh_time=0.3, extra_info=None,
            buffer=1024, selector=None):
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
        self.refresh_time = refresh_time

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
                rlist, __, __ = self.selector(self.pipes, [], [], 1.0)
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
