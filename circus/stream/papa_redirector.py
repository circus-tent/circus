from zmq.eventloop import ioloop
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

    @staticmethod
    def get_process_pipes(process):
        if process.pipe_stdout or process.pipe_stderr:
            yield 'output', process.output
