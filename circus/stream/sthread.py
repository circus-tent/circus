from threading import Thread
import select
import time

from circus.stream.base import BaseRedirector


class Redirector(BaseRedirector, Thread):
    def __init__(self, redirect, refresh_time=0.3, extra_info=None,
            buffer=1024):
        Thread.__init__(self)
        BaseRedirector.__init__(self, redirect, refresh_time=refresh_time,
                extra_info=extra_info, buffer=buffer,
                selector=select.select)
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self._select()
            time.sleep(self.refresh_time)

    def kill(self):
        if not self.running:
            return
        self.running = False
        self.join()
