from circus.controller import Controller as _Controller
from circus.green.sighandler import SysHandler

from zmq.green.eventloop import ioloop, zmqstream
from gevent.coros import RLock
from gevent import sleep


class Controller(_Controller):
    def __init__(self, endpoint, multicast_endpoint, context, loop, arbiter,
                 check_delay=1.0):
        super(Controller, self).__init__(endpoint, multicast_endpoint,
                                         context, loop, arbiter,
                                         check_delay)
        self._lock = RLock()
        self._started = False

    def _init_syshandler(self):
        self.sys_hdl = SysHandler(self)

    def _init_stream(self):
        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def dispatch(self, job):
        try:
            return _Controller.dispatch(self, job)
        finally:
            sleep(0)

    def start(self):
        cbk = ioloop.PeriodicCallback
        self._lock.acquire()
        try:
            if self._started:
                return True
            self.initialize()
            self.caller = cbk(self.arbiter.manage_watchers,
                              self.check_delay, self.loop)
            self.caller.start()
            self._started = True
        finally:
            self._lock.release()
