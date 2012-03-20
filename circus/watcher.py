import errno
import signal
import time

from zmq.utils.jsonapi import jsonmod as json

from circus.process import Process, DEAD_OR_ZOMBIE
from circus import logger
from circus import util


class Watcher(object):

    def __init__(self, name, cmd, numprocesses=1, warmup_delay=0.,
                 working_dir=None, shell=False, uid=None,
                 gid=None, send_hup=False, env=None, stopped=False,
                 times=2, within=1., retry_in=7., max_retry=5,
                 graceful_timeout=30., prereload_fn=None):
        """ init
        """
        self.name = name
        self.res_name = name.lower().replace(" ", "_")
        self.numprocesses = int(numprocesses)
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self._process_counter = 0
        self.stopped = stopped
        self.times = times
        self.within = within
        self.retry_in = retry_in
        self.max_retry = max_retry
        self.graceful_timeout = 30
        self.prereload_fn = prereload_fn

        self.optnames = ("numprocesses", "warmup_delay", "working_dir",
                         "uid", "gid", "send_hup", "shell", "env",
                         "cmd", "times", "within", "retry_in",
                         "max_retry", "graceful_timeout")

        if not working_dir:
            # working dir hasn't been set
            working_dir = util.get_working_dir()

        self.working_dir = working_dir

        self.processes = {}
        self.shell = shell
        self.uid = uid
        self.gid = gid
        self.env = env
        self.send_hup = send_hup
        self.evpub_socket = None

    @util.debuglog
    def initialize(self, evpub_socket):
        self.evpub_socket = evpub_socket

    def __len__(self):
        return len(self.processes)

    def send_msg(self, topic, msg):
        """send msg"""

        json_msg = json.dumps(msg)
        if isinstance(json_msg, unicode):
            json_msg = json_msg.encode('utf8')

        if isinstance(self.res_name, unicode):
            name = self.res_name.encode('utf8')
        else:
            name = self.res_name

        multipart_msg = ["show.%s.%s" % (name, topic), json.dumps(msg)]

        if not self.evpub_socket.closed:
            self.evpub_socket.send_multipart(multipart_msg)

    @util.debuglog
    def reap_processes(self):
        """Reap processes.
        """
        if self.stopped:
            return

        for wid, process in self.processes.items():
            if process.poll() is not None:
                if process.status == DEAD_OR_ZOMBIE:
                    process.stop()

                self.send_msg("reap", {"process_id": wid,
                                       "process_pid": process.pid,
                                       "time": time.time()})
                if self.stopped:
                    break
                self.processes.pop(wid)

    @util.debuglog
    def manage_processes(self):
        """ manage processes
        """
        if self.stopped:
            return

        if len(self.processes.keys()) < self.numprocesses:
            self.spawn_processes()

        processes = self.processes.keys()
        processes.sort()
        while len(processes) > self.numprocesses:
            wid = processes.pop(0)
            process = self.processes.pop(wid)
            self.kill_process(process)

    @util.debuglog
    def reap_and_manage_processes(self):
        """Reap & manage processes.
        """
        if self.stopped:
            return
        self.reap_processes()
        self.manage_processes()

    @util.debuglog
    def spawn_processes(self):
        """Spawn processes.
        """
        for i in range(self.numprocesses - len(self.processes.keys())):
            self.spawn_process()
            time.sleep(self.warmup_delay)

    def spawn_process(self):
        """Spawn process.
        """
        if self.stopped:
            return

        self._process_counter += 1
        nb_tries = 0
        while nb_tries < self.max_retry:
            process = None
            try:
                process = Process(self._process_counter, self.cmd,
                          working_dir=self.working_dir, shell=self.shell,
                          uid=self.uid, gid=self.gid, env=self.env)
                self.processes[self._process_counter] = process
                logger.info('running %s process [pid %d]' % (self.name,
                            process.pid))
            except OSError, e:
                logger.warning('error in %r: %s' % (self.name, str(e)))

            if process is None:
                nb_tries += 1
                continue
            else:
                self.send_msg("spawn", {"process_id": process.wid,
                                        "process_pid": process.pid,
                                        "time": time.time()})
                time.sleep(self.warmup_delay)
                return

        self.stop()

    def kill_process(self, process, sig=signal.SIGTERM):
        """Kill process.
        """
        self.send_msg("kill", {"process_id": process.wid,
                               "time": time.time()})
        logger.info("%s: kill process %s" % (self.name, process.pid))
        process.send_signal(sig)

    @util.debuglog
    def kill_processes(self, sig):
        """Kill processes.
        """
        for wid in self.processes.keys():
            try:
                process = self.processes.pop(wid)
                self.kill_process(process, sig)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    @util.debuglog
    def send_signal(self, wid, signum):
        self.processes[wid].send_signal(signum)

    def send_signal_processes(self, signum):
        for _, process in self.processes.items():
            try:
                process.send_signal(signum)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    @util.debuglog
    def send_signal_child(self, wid, pid, signum):
        """Send signal to a child.
        """
        process = self.processes[int(wid)]
        try:
            process.send_signal_child(int(pid), signum)
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise

    @util.debuglog
    def send_signal_children(self, wid, signum):
        """Send signal to all children.
        """
        process = self.processes[int(wid)]
        process.send_signal_children(signum)

    @util.debuglog
    def status(self):
        if self.stopped:
            return "stopped"
        return "active"

    @util.debuglog
    def process_info(self, wid):
        process = self.processes[int(wid)]
        return process.info()

    @util.debuglog
    def info(self):
        return dict([(fid, proc.info()) for fid, proc in
                     self.processes.items()])

    @util.debuglog
    def stop(self, graceful=True):
        """Stop.
        """
        self.stopped = True

        sig = signal.SIGQUIT
        if not graceful:
            sig = signal.SIGTERM

        limit = time.time() + self.graceful_timeout
        while self.processes and time.time() < limit:
            self.kill_processes(sig)
            time.sleep(0.1)

            # reap processes
            for wid, process in self.processes.items():
                if process.poll() is not None:
                    del self.processes[wid]

        self.kill_processes(signal.SIGKILL)
        self.send_msg("stop", {"time": time.time()})
        logger.info('%s stopped' % self.name)

    @util.debuglog
    def start(self):
        """Start.
        """
        if not self.stopped:
            return

        self.stopped = False
        self.reap_processes()
        self.manage_processes()
        logger.info('%s started' % self.name)
        self.send_msg("start", {"time": time.time()})

    @util.debuglog
    def restart(self):
        """Restart.
        """
        self.send_msg("restart", {"time": time.time()})
        self.stop()
        self.start()
        logger.info('%s restarted' % self.name)

    @util.debuglog
    def reload(self, graceful=True):
        """ reload
        """
        if self.prereload_fn is not None:
            self.prereload_fn(self)

        if not graceful:
            return self.restart()

        if self.send_hup:
            for wid, process in self.processes.items():
                logger.info("SEND HUP to %s [%s]" % (wid, process.pid))
                process.send_signal(signal.SIGHUP)
        else:
            for i in range(self.numprocesses):
                self.spawn_process()
            self.manage_processes()
        self.send_msg("reload", {"time": time.time()})

    @util.debuglog
    def incr(self):
        self.numprocesses += 1
        self.manage_processes()
        return self.numprocesses

    @util.debuglog
    def decr(self):
        if self.numprocesses > 0:
            self.numprocesses -= 1
            self.manage_processes()
        return self.numprocesses

    def get_process(self, wid):
        return self.processes[wid]

    def set_opt(self, key, val):
        """Set a show option.

        This function set the show options. unknown keys are ignored.
        This function return an action number:

        - 0: trigger the process management
        - 1: trigger a graceful reload of the processes;
        """

        action = 0
        if key == "numprocesses":
            self.numprocesses = int(val)
        elif key == "warmup_delay":
            self.warmup_delay = float(val)
        elif key == "working_dir":
            self.working_dir = val
            action = 1
        elif key == "uid":
            self.uid = util.to_uid(val)
            action = 1
        elif key == "gid":
            self.gid = util.to_gid(val)
            action = 1
        elif key == "send_hup":
            self.send_hup = val
        elif key == "shell":
            self.shell = val
            action = 1
        elif key == "env":
            self.env = val
            action = 1
        elif key == "cmd":
            self.cmd = val
            action = 1
        elif key == "times":
            self.times = int(val)
            action = -1
        elif key == "within":
            self.within = float(val)
        elif key == "retry_in":
            self.retry_in = float(val)
        elif key == "max_retry":
            self.max_retry = int(val)
        elif key == "graceful_timeout":
            self.graceful_timeout = float(val)
            action = -1

        # send update event
        self.send_msg("updated", {"time": time.time()})
        return action

    def do_action(self, num):
        # trigger needed action
        self.stopped = False
        if num == 1:
            for i in range(self.numprocesses):
                self.spawn_process()
            self.manage_processes()
        else:
            self.reap_and_manage_processes()

    @util.debuglog
    def options(self, *args):
        return [(name, getattr(self, name)) for name in sorted(self.optnames)]
