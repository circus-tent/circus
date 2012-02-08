from subprocess import Popen, PIPE, STDOUT
import sys
import os
import time

from circus.controller import Controller


class Workers(list):

    WORKERS = []
    PIPE = []


    def __init__(self, num_workers, cmd, check_delay, warmup_delay, endpoint):
        self.cmd = cmd
        self.num_workers = num_workers
        self.check_delay = check_delay
        self.warmup_delay = warmup_delay
        self.ctrl = Controller(endpoint, self, self.check_delay)
        self.running = False


    def run(self):
        self.manage_workers()
        while True:
            try:
                self.reap_workers()
                self.manage_workers()

                self.ctrl.poll()
            except KeyboardInterrupt:
                self.halt()
            except SystemExit:
                raise


    def reap_workers(self):
        for worker in self.WORKERS:
            if worker.poll() is not None:
                self.WORKERS.pop(worker)

    def manage_workers(self):
        if len(self.WORKERS) < self.num_workers:
            self.spawn_workers()

        workers = self.WORKERS

        workers.sort()
        while len(workers) > self.num_workers:
            worker = workers.pop(0)
            self.kill_worker(worker)


    def spawn_workers(self):
        for i in range(self.num_workers - len(self.WORKERS)):
            self.spawn_worker()

    def spawn_worker(self):
        index = len(self)
        run = self.cmd % index
        print run
        worker = Popen(run.split())   #, stdout=PIPE, stderr=PIPE)
        print 'running worker pid %d' % res.pid
        self.WORKERS.append(worker)


    # TODO: we should manage more workers here.
    def kill_worker(self, worker):
        worker.terminate()

    def kill_workers(self, worker):
        for worker in self.WORKERS:
            worker.terminate()


    def halt(self, exit_code=0):
        self.terminate()
        sys.exit(exit_code)


    def terminate(self):
        self.kill_workers()
        self.ctrl.terminate()


