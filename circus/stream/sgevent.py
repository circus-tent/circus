from gevent import Greenlet, sleep
from gevent.select import select

from circus.stream.base import BaseRedirector


class Redirector(BaseRedirector, Greenlet):
    def __init__(self, redirect, refresh_time=0.3, extra_info=None,
            buffer=1024):
        Greenlet.__init__(self)
        BaseRedirector.__init__(self, redirect, refresh_time=refresh_time,
                extra_info=extra_info, buffer=buffer, selector=select)

    def _run(self, *args, **kwargs):
        while True:
            self._select()
            sleep(self.refresh_time)
