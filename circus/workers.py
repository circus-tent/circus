from subprocess import Popen, PIPE, STDOUT
import sys
import os
import time

from circus.controller import Controller


class Workers(list):

    def __init__(self, size, cmd, check_delay, warmup_delay, endpoint):
        self.cmd = cmd
        self.size = size
        self.check_delay = check_delay
        self.warmup_delay = warmup_delay
        self.ctrl = Controller(endpoint, self, self.check_delay)
        self.running = False

    def _run(self):
        index = len(self)
        run = self.cmd % index
        print run
        res = Popen(run.split())   #, stdout=PIPE, stderr=PIPE)
        print 'running worker pid %d' % res.pid
        return res

    def run(self):
        self.running = True

        for i in range(self.size):
            self.append(self._run())
            time.sleep(self.warmup_delay)

        while self.running:
            self.check()
            self.ctrl.poll()

    def check(self):
        for worker in self:
            res = worker.poll()
            if res is not None:
                # respawn a worker
                print 'respawning!'
                self.remove(worker)
                self.append(self._run())

    def terminate(self):
        self.running = False
        for worker in self:
            worker.terminate()
        self.ctrl.terminate()
