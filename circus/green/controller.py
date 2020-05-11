from circus.controller import Controller as _Controller
from circus.green.sighandler import SysHandler

from zmq.green.eventloop import ioloop, zmqstream


class Controller(_Controller):

    def _init_syshandler(self):
        self.sys_hdl = SysHandler(self)

    def _init_stream(self):
        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def start(self):
        self.loop.make_current()
        self.initialize()
        self.caller = ioloop.PeriodicCallback(self.arbiter.manage_watchers,
                                              self.check_delay)
        self.caller.start()
