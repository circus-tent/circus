from circus.arbiter import Arbiter as _Arbiter
from circus.arbiter import ThreadedArbiter as _ThreadedArbiter
from circus.green.controller import Controller

from zmq.green.eventloop import ioloop
from zmq.green import Context
from gevent.coros import RLock
from gevent import sleep


class Arbiter(_Arbiter):
    def _init_context(self, context):
        self.context = context or Context.instance()
        self.loop = ioloop.IOLoop.instance()
        self._started = False
        self.ctrl = Controller(self.endpoint, self.multicast_endpoint,
                               self.context, self.loop, self, self.check_delay)

    def manage_watchers(self):
        sleep(0)
        return _Arbiter.manage_watchers()


class ThreadedArbiter(_ThreadedArbiter):
    def __init__(self, *args, **kw):
        _ThreadedArbiter.__init__(self, *args, **kw)
        self._lock = RLock()
        self._started = False
        self.loop.add_callback(self._wakeup_gevent)

    def _wakeup_gevent(self):
        sleep(0)
        if self._started:
            self.loop.add_callback(self._wakeup_gevent)

    def start(self):
        self._lock.acquire()
        try:
            if self._started:
                return True
            super(ThreadedArbiter, self).start()
            self._started = True
        finally:
            self._lock.release()

    def _init_context(self, context):
        self.context = context or Context.instance()
        self.loop = ioloop.IOLoop.instance()
        self.ctrl = Controller(self.endpoint, self.multicast_endpoint,
                               self.context, self.loop, self, self.check_delay)
