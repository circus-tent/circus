from threading import Thread
import select
import time

from circus.stream.base import BaseRedirector

class Redirector(BaseRedirector, Thread):
    def __init__(self, redirect, extra_info=None, buffer=1024):
        Thread.__init__(self)
        BaseRedirector.__init__(self, redirect, extra_info, buffer)
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self._select()
            time.sleep(0.3)

    def kill(self):
        if not self.running:
            return
        self.running = False
        self.join()
