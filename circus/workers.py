import errno
import os
from subprocess import Popen
import sys

from circus.controller import Controller


class Worker(Popen):
    # XXX will hold stats and other info
    def __init__(self, cmd):
        Popen.__init__(self, cmd.split())
        self.started = time.time()

    def age(self):
        return time.time() - self.started


class Workers(object):

    def __init__(self, num_workers, cmd, check_delay, warmup_delay, endpoint):
        self.cmd = cmd
        self.num_workers = num_workers
        self.check_delay = check_delay
        self.warmup_delay = warmup_delay
        self.ctrl = Controller(endpoint, self, self.check_delay)
        self.pid = os.getpid()
        self.worker_age = 0
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
        self.worker_age += 1
        worker = Worker(self.cmd.split())
        print 'running worker pid %d' % worker.pid
        self.workers[self.worker_age] = worker

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
