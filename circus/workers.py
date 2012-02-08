import errno
import os
import signal
from subprocess import Popen, PIPE, STDOUT
import sys
import time

import zmq

from circus.controller import Controller


class Workers(object):

    WORKERS = []

    SIGNALS = map(
        lambda x: getattr(signal, "SIG%s" % x),
        "HUP QUIT INT TERM WINCH".split()
    )

    SIG_NAMES = dict(
        (getattr(signal, name), name[3:].lower()) for name in dir(signal)
    )

    def __init__(self, num_workers, cmd, check_delay, warmup_delay, endpoint):
        self.cmd = cmd
        self.num_workers = num_workers
        self.check_delay = check_delay
        self.warmup_delay = warmup_delay
        self.ctrl = Controller(endpoint, self, self.check_delay)
        self.pid = os.getpid()

        # set zmq socket
        self.ctx = zmq.Context()
        self.skt = self.ctx.socket(zmq.REQ)
        self.skt.connect(endpoint)

        # init signals
        map(lambda s: signal.signal(s, self.signal), self.SIGNALS)
        signal.signal(signal.SIGCHLD, self.handle_chld)

        print "Starting master on pid %s" % self.pid

    def signal(self, sig, frame):
        if sig in self.SIG_NAMES:
            signame = self.SIG_NAMES.get(sig)
            self.skt.send(signame)


    def handle_chld(self, *args):
        pass

    def handle_hup(self):
        pass

    def handle_quit(self):
        self.halt()

    def handle_int(self):
        self.halt()

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
        worker = Popen(self.cmd.split())   #, stdout=PIPE, stderr=PIPE)
        print 'running worker pid %d' % worker.pid
        self.WORKERS.append(worker)


    # TODO: we should manage more workers here.
    def kill_worker(self, worker):
        worker.terminate()

    def kill_workers(self):
        for worker in self.WORKERS:
            try:
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


