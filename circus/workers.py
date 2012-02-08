import errno
import os
from subprocess import Popen
import sys
import time

from circus.controller import Controller


class Worker(object):
    # XXX will hold stats and other info
    def __init__(self, wid, cmd):
        self.wid = str(wid)
        self.cmd = cmd.replace('$WID', self.wid)
        self._worker = Popen(self.cmd.split())
        self.started = time.time()

    def poll(self):
        return self._worker.poll()

    def terminate(self):
        return self._worker.terminate()

    def age(self):
        return time.time() - self.started

    @property
    def pid(self):
        return self._worker.pid


class Workers(object):

    def __init__(self, num_workers, cmd, check_delay, warmup_delay, endpoint):
        self.cmd = cmd
        self.num_workers = num_workers
        self.check_delay = check_delay
        self.warmup_delay = warmup_delay
        self.ctrl = Controller(endpoint, self, self.check_delay)
        self.pid = os.getpid()
        self._worker_counter = 0
        self.workers = {}
        print "Starting master on pid %s" % self.pid

    def handle_reload(self):
        pass

    def handle_quit(self):
        self.halt()

    def run(self):
        self.manage_workers()
        while True:
            self.reap_workers()
            self.manage_workers()
            self.ctrl.poll()

    def reap_workers(self):
        for wid, worker in self.workers.items():
            if worker.poll() is not None:
                self.workers.pop(wid)

    def manage_workers(self):
        if len(self.workers.keys()) < self.num_workers:
            self.spawn_workers()

        workers = self.workers.keys()
        workers.sort()
        while len(workers) > self.num_workers:
            wid = workers.pop(0)
            worker = self.workers.pop(wid)
            self.kill_worker(worker)

    def spawn_workers(self):
        for i in range(self.num_workers - len(self.workers.keys())):
            self.spawn_worker()

    def spawn_worker(self):
        self._worker_counter += 1
        worker = Worker(self._worker_counter, self.cmd)
        print 'running worker pid %d' % worker.pid
        self.workers[self._worker_counter] = worker

    # TODO: we should manage more workers here.
    def kill_worker(self, worker):
        print "kill worker %s" % worker.pid
        worker.terminate()

    def kill_workers(self):
        for wid in self.workers.keys():
            try:
                worker = self.workers.pop(wid)
                self.kill_worker(worker)
            except OSError, e:
                if e.errno != errno.ESRCH:
                    raise

    def halt(self, exit_code=0):
        self.terminate()
        sys.exit(exit_code)

    def terminate(self):
        self.kill_workers()
        self.ctrl.terminate()
