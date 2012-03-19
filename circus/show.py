import errno
import json
import signal
import time

from circus.fly import Fly, DEAD_OR_ZOMBIE
from circus import logger
from circus import util


class Show(object):

    def __init__(self, name, cmd, numflies=1, warmup_delay=0.,
                 working_dir=None, shell=False, uid=None,
                 gid=None, send_hup=False, env=None, stopped=False,
                 times=2, within=1., retry_in=7., max_retry=5,
                 graceful_timeout=30., prereload_fn=None):
        """ init
        """
        self.name = name

        self.res_name = name.lower().replace(" ", "_")
        self.numflies = int(numflies)
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self._fly_counter = 0
        self.stopped = stopped
        self.times = times
        self.within = within
        self.retry_in = retry_in
        self.max_retry = max_retry
        self.graceful_timeout = 30
        self.prereload_fn = prereload_fn

        self.optnames = ("numflies", "warmup_delay", "working_dir",
                         "uid", "gid", "send_hup", "shell", "env",
                         "cmd", "times", "within", "retry_in",
                         "max_retry", "graceful_timeout")

        if not working_dir:
            # working dir hasn't been set
            working_dir = util.get_working_dir()

        self.working_dir = working_dir

        self.flies = {}
        self.shell = shell
        self.uid = uid
        self.gid = gid
        self.env = env
        self.send_hup = send_hup
        self.evpub_socket = None

    def initialize(self, evpub_socket):
        self.evpub_socket = evpub_socket

    def __len__(self):
        return len(self.flies)

    def send_msg(self, topic, msg):
        """send msg"""
        multipart_msg = ["show.%s.%s" % (self.res_name, topic),
                         json.dumps(msg)]

        if not self.evpub_socket.closed:
            self.evpub_socket.send_multipart(multipart_msg)

    @util.debuglog
    def reap_flies(self):
        """ reap flies
        """
        if self.stopped:
            return

        for wid, fly in self.flies.items():
            if fly.poll() is not None:
                if fly.status == DEAD_OR_ZOMBIE:
                    fly.stop()

                self.send_msg("reap", {"fly_id": wid,
                                       "fly_pid": fly.pid,
                                       "time": time.time()})
                if self.stopped:
                    break
                self.flies.pop(wid)

    @util.debuglog
    def manage_flies(self):
        """ manage flies
        """
        if self.stopped:
            return

        if len(self.flies.keys()) < self.numflies:
            self.spawn_flies()

        flies = self.flies.keys()
        flies.sort()
        while len(flies) > self.numflies:
            wid = flies.pop(0)
            fly = self.flies.pop(wid)
            self.kill_fly(fly)

    @util.debuglog
    def reap_and_manage_flies(self):
        """ reap +manage flies
        """
        if self.stopped:
            return
        self.reap_flies()
        self.manage_flies()

    @util.debuglog
    def spawn_flies(self):
        """ spawn flies
        """
        for i in range(self.numflies - len(self.flies.keys())):
            self.spawn_fly()
            time.sleep(self.warmup_delay)

    def spawn_fly(self):
        """ spawn fly
        """
        if self.stopped:
            return

        self._fly_counter += 1
        nb_tries = 0
        while nb_tries < self.max_retry:
            fly = None
            try:
                fly = Fly(self._fly_counter, self.cmd,
                          working_dir=self.working_dir, shell=self.shell,
                          uid=self.uid, gid=self.gid, env=self.env)
                self.flies[self._fly_counter] = fly
                logger.info('running %s fly [pid %d]' % (self.name, fly.pid))
            except OSError, e:
                logger.warning('error in %r: %s' % (self.name, str(e)))

            if fly is None:
                nb_tries += 1
                continue
            else:
                self.send_msg("spawn", {"fly_id": fly.wid,
                                        "fly_pid": fly.pid,
                                        "time": time.time()})
                time.sleep(self.warmup_delay)
                return

        self.stop()

    def kill_fly(self, fly, sig=signal.SIGTERM):
        """ kill fly
        """
        self.send_msg("kill", {"fly_id": fly.wid, "time": time.time()})
        logger.info("%s: kill fly %s" % (self.name, fly.pid))
        fly.send_signal(sig)

    @util.debuglog
    def kill_flies(self, sig):
        """ kill flies
        """
        for wid in self.flies.keys():
            try:
                fly = self.flies.pop(wid)
                self.kill_fly(fly, sig)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    @util.debuglog
    def send_signal(self, wid, signum):
        self.flies[wid].send_signal(signum)

    def send_signal_flies(self, signum):
        for fly in self.flies:
            try:
                fly.send_signal(signum)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    @util.debuglog
    def send_signal_child(self, wid, pid, signum):
        """ send signal child
        """
        fly = self.flies[int(wid)]
        try:
            fly.send_signal_child(int(pid), signum)
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise

    @util.debuglog
    def send_signal_children(self, wid, signum):
        """ send signal children
        """
        fly = self.flies[int(wid)]
        fly.send_signal_children(signum)

    @util.debuglog
    def status(self):
        if self.stopped:
            return "stopped"
        return "active"

    @util.debuglog
    def fly_info(self, wid):
        fly = self.flies[int(wid)]
        return fly.info()

    @util.debuglog
    def info(self):
        return [fly.info() for _, fly in self.flies.items()]

    @util.debuglog
    def stop(self, graceful=True):
        """ stop
        """
        self.stopped = True

        sig = signal.SIGQUIT
        if not graceful:
            sig = signal.SIGTERM

        limit = time.time() + self.graceful_timeout
        while self.flies and time.time() < limit:
            self.kill_flies(sig)
            time.sleep(0.1)
            # reap flies
            for wid, fly in self.flies.items():
                if fly.poll() is not None:
                    del self.flies[wid]
        self.kill_flies(signal.SIGKILL)

        self.send_msg("stop", {"time": time.time()})
        logger.info('%s stopped' % self.name)

    @util.debuglog
    def start(self):
        """ start
        """
        if not self.stopped:
            return

        self.stopped = False
        self.reap_flies()
        self.manage_flies()
        logger.info('%s started' % self.name)
        self.send_msg("start", {"time": time.time()})

    @util.debuglog
    def restart(self):
        """ restart
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
            for wid, fly in self.flies.items():
                logger.info("SEND HUP to %s [%s]" % (wid, fly.pid))
                fly.send_signal(signal.SIGHUP)
        else:
            for i in range(self.numflies):
                self.spawn_fly()
            self.manage_flies()
        self.send_msg("reload", {"time": time.time()})

    @util.debuglog
    def incr(self):
        self.numflies += 1
        self.manage_flies()
        return self.numflies

    @util.debuglog
    def decr(self):
        if self.numflies > 0:
            self.numflies -= 1
            self.manage_flies()
        return self.numflies

    def get_fly(self, wid):
        return self.flies[wid]

    def set_opt(self, key, val):
        """ set a show option

        This function set the show options. unknown keys are ignored.
        This function return an action number:

        - 0: trigger the process management
        - 1: trigger a graceful reload of the flies;
        """

        action = 0
        if key == "numflies":
            self.numflies = int(val)
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
            self.send_hup = util.to_bool(val)
        elif key == "shell":
            self.shell = util.to_bool(val)
            action = 1
        elif key == "env":
            self.env = util.parse_env(val)
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
            for i in range(self.numflies):
                self.spawn_fly()
            self.manage_flies()
        else:
            self.reap_and_manage_flies()

    def get_opt(self, name):
        """ get opt
        """
        val = getattr(self, name)
        if name == "env":
            val = util.env_to_str(val)
        else:
            if val is None:
                val = ""
            else:
                val = str(val)
        return val

    @util.debuglog
    def options(self, *args):
        return [(name, self.get_opt(name)) for name in sorted(self.optnames)]
