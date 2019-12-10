from tornado import ioloop
from circus.stream import Redirector


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
            return self.do_read(fd)

        def do_read(self, fd):
            out, err, close = self.pipe.read()
            for output_type, output_list in (('stdout', out), ('stderr', err)):
                if output_list:
                    for line in output_list:
                        datamap = {'data': line.data,
                                   'pid': self.process.pid,
                                   'name': output_type,
                                   'timestamp': line.timestamp}
                        self.redirector.redirect[output_type](datamap)
            self.pipe.acknowledge()
            if close:
                self.redirector.remove_fd(fd)

    def stop(self):
        count = 0
        for fd, handler in list(self._active.items()):
            # flush whatever is pending
            if handler.pipe.ready:
                handler.do_read(fd)
            count += self._stop_one(fd)
        self.running = False
        return count

    @staticmethod
    def get_process_pipes(process):
        if process.pipe_stdout or process.pipe_stderr:
            yield 'output', process.output
