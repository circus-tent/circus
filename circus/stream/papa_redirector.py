import errno
import os
import sys

from zmq.eventloop import ioloop
from circus.stream import Redirector
from circus.util import papa


class PapaRedirector(Redirector):

    class Handler(Redirector.Handler):
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
                    datamap.update(self.redirector.extra_info)
                    self.redirector.redirect(datamap)
            except IOError as ex:
                if ex.args[0] != errno.EAGAIN:
                    raise
                try:
                    sys.exc_clear()
                except Exception:
                    pass

    @staticmethod
    def get_process_pipes(process):
        if process.pipe_stdout or process.pipe_stderr:
            yield 'watcher', process.watcher
