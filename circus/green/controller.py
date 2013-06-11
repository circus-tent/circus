from circus.controller import Controller as _Controller
from circus.green.sighandler import SysHandler

from zmq.green.eventloop import ioloop, zmqstream


class Controller(_Controller):

    def __init__(self, endpoint, multicast_endpoint, context, loop, arbiter,
                 check_delay=1.0):
        super(Controller, self).__init__(self)
        self.sys_hdl = SysHandler(self)

    def _init_stream(self):
        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def start(self):
        self.initialize()
        self.caller = ioloop.PeriodicCallback(self.wakeup, self.check_delay,
                                              self.loop)
        self.caller.start()
