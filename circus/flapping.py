from threading import Timer
import time

from circus import logger

class Flapping(object):

    def __init__(self, show, times=2, within=1., retry_in=7.,
            max_retry=5):
        self.show = show
        self.times = times
        self.within = within
        self.retry_in = retry_in
        self.max_retry = max_retry

        self.tries = 0
        self.timeline = []
        self.timer = None


    def notify(self):
        self.timeline.append(time.time())
        self.check()

    def reset(self):
        self.timeline = []
        self.tries = 0
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def check(self):
        if len(self.timeline) == self.times:
            duration = self.timeline[-1] - self.timeline[0]
            if duration <= self.within:
                if self.tries <  self.max_retry:
                    logger.info("%s: flapping detected: retry in %2ds" %
                            (self.show.name, self.retry_in))
                    self.show.stopped = True
                    self.timeline = []
                    self.tries += 1
                    self.timer = Timer(self.retry_in, self.show.start)
                    self.timer.start()
                else:
                    logger.info("%s: flapping detected: max retry limit" %
                            self.show.name)
                    self.timeline = []
                    self.tries = 0
                    self.show.stop()
            else:
                self.timeline = []
                self.tries = 0
