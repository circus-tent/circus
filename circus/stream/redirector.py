import errno
import os
import sys

from tornado import ioloop


class Redirector(object):

    class Handler(object):
        def __init__(self, redirector, name, process, pipe):
            self.redirector = redirector
            self.name = name
            self.process = process
            self.pipe = pipe

        def __call__(self, fd, events):
            if not (events & ioloop.IOLoop.READ):
                if events == ioloop.IOLoop.ERROR:
                    self.redirector.remove_fd(fd)
                return
            try:
                data = os.read(fd, self.redirector.buffer)
                if len(data) == 0:
                    self.redirector.remove_fd(fd)
                else:
                    datamap = {'data': data, 'pid': self.process.pid,
                               'name': self.name}
                    self.redirector.redirect[self.name](datamap)
            except IOError as ex:
                if ex.args[0] != errno.EAGAIN:
                    raise
                try:
                    sys.exc_clear()
                except Exception:
                    pass

    def __init__(self, stdout_redirect, stderr_redirect, buffer=1024,
                 loop=None):
        self.running = False
        self.pipes = {}
        self._active = {}
        self.redirect = {'stdout': stdout_redirect, 'stderr': stderr_redirect}
        self.buffer = buffer
        self.loop = loop or ioloop.IOLoop.current()

    def _start_one(self, fd, stream_name, process, pipe):
        if fd not in self._active:
            handler = self.Handler(self, stream_name, process, pipe)
            self.loop.add_handler(fd, handler, ioloop.IOLoop.READ)
            self._active[fd] = handler
            return 1
        return 0

    def start(self):
        count = 0
        for fd, value in self.pipes.items():
            name, process, pipe = value
            count += self._start_one(fd, name, process, pipe)
        self.running = True
        return count

    def _stop_one(self, fd):
        if fd in self._active:
            self.loop.remove_handler(fd)
            del self._active[fd]
            return 1
        return 0

    def stop(self):
        count = 0
        for fd in list(self._active.keys()):
            count += self._stop_one(fd)
        self.running = False
        return count

    @staticmethod
    def get_process_pipes(process):
        if process.pipe_stdout:
            yield 'stdout', process.stdout
        if process.pipe_stderr:
            yield 'stderr', process.stderr

    def add_redirections(self, process):
        for name, pipe in self.get_process_pipes(process):
            fd = pipe.fileno()
            self._stop_one(fd)
            self.pipes[fd] = name, process, pipe
            if self.running:
                self._start_one(fd, name, process, pipe)
        process.redirected = True

    def remove_fd(self, fd):
        self._stop_one(fd)
        if fd in self.pipes:
            del self.pipes[fd]

    def remove_redirections(self, process):
        for _, pipe in self.get_process_pipes(process):
            try:
                fileno = pipe.fileno()
            except ValueError:
                # the pipe was already closed
                pass
            else:
                self.remove_fd(fileno)
        process.redirected = False

    def change_stream(self, stream_name, redirect_writer):
        self.redirect[stream_name] = redirect_writer

    def get_stream(self, stream_name):
        return self.redirect.get(stream_name)
