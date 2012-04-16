import gevent_zeromq    # just to make sure zmq will not block  # NOQA
from gevent import Greenlet
from gevent.select import select

from circus.stream.base import BaseRedirector

class Redirector(BaseRedirector, Greenlet):
    def __init__(self, redirect, extra_info=None, buffer=1024):
        Greenlet.__init__(self)
        BaseRedirector.__init__(self, redirect, extra_info, buffer,
                                selector=select)

    def _run(self, *args, **kwargs):
        while True:
            self._select()
