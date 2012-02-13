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

class Program(object):

    def __init__(self, name, cmd, num_workers, warmup_delay):
        self.name = name
        self.num_workers = num_workers
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self._worker_counter = 0
        self.workers = {}

    def __len__(self):
        return len(self.workers)

    def handle_numworkers(self, *args):
        return str(self.num_workers)

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
            time.sleep(self.warmup_delay)

    def spawn_worker(self):
        self._worker_counter += 1
        worker = Worker(self._worker_counter, self.cmd)
        print 'running %s worker [pid %d]' % (self.name, worker.pid)
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

    def handle_quit(self, *args):
        self.kill_workers()
        self.num_workers = 0
        return "ok"

    def handle_reload(self, *args):
        for i in range(self.num_workers):
            self.spawn_worker()
        self.manage_workers()
        return "ok"
    handle_hup = handle_reload

    def handle_ttin(self, *args):
        self.num_workers += 1
        self.manage_workers()
        return str(self.num_workers)

    def handle_ttou(self, *args):
        self.num_workers -= 1
        self.manage_workers()
        return str(self.num_workers)

class Manager(object):

    def __init__(self, programs, check_delay, endpoint, ipc_path):
        self.programs = programs
        self.check_delay = check_delay
        self.ipc_path = ipc_path
        self.ctrl = Controller(endpoint, self, self.check_delay,
                self.ipc_path)
        self.pid = os.getpid()

        self._programs_names = {}
        self.setup()
        print "Starting master on pid %s" % self.pid

    def setup(self):
        for program in self.programs:
            self._programs_names[program.name] = program

    def get_program(self, name):
        return self._programs_names[name]

    def list_programs(self):
        return ",".join(self._programs_names.keys())

    def handle_reload(self):
        return "ok"

    def handle_quit(self):
        self.halt()

    def handle_winch(self):
        "SIGWINCH handling"
        if os.getppid() == 1 or os.getpgrp() != os.getpid():
            for program in self.programs:
                program.num_workers = 0
                program.kill_workers()
        else:
            # SIGWINCH ignored. Not daemonized
            pass

    def num_workers(self):
        l = 0
        for program in self.programs:
            l += len(program)
        return l

    def run(self):
        # launch workers
        for program in self.programs:
            program.manage_workers()

        while True:
            # manage and reap workers
            for program in self.programs:
                program.reap_workers()
                program.manage_workers()

            # wait for the controller
            self.ctrl.poll()


    def halt(self, exit_code=0):
        self.terminate()
        sys.exit(exit_code)

    def terminate(self):
        # kill workers
        for program in self.programs:
            program.kill_workers()

        self.ctrl.terminate()
