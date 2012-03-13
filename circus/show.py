import errno
import signal
import time

from circus.flapping import Flapping
from circus.fly import Fly
from circus import logger
from circus import util


class Show(object):

    def __init__(self, name, cmd, numflies=1, warmup_delay=0.,
                 working_dir=None, shell=False, uid=None,
                 gid=None, send_hup=False, env=None, stopped=False,
                 times=2, within=1., retry_in=7., max_retry=5,
                 graceful_timeout=30., prereload_fn=None):
        self.name = name
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

        # define flapping object
        self.flapping = Flapping(self, times, within, retry_in, max_retry)

    def __len__(self):
        return len(self.flies)

    @util.debuglog
    def reap_flies(self):
        if self.stopped:
            return

        for wid, fly in self.flies.items():
            if fly.poll() is not None:
                self.flapping.notify()
                if self.stopped:
                    break
                self.flies.pop(wid)

    @util.debuglog
    def manage_flies(self):
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
        if self.stopped:
            return
        self.reap_flies()
        self.manage_flies()

    @util.debuglog
    def spawn_flies(self):
        for i in range(self.numflies - len(self.flies.keys())):
            self.spawn_fly()
            time.sleep(self.warmup_delay)

    def spawn_fly(self):
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
                return

        self.stop()

    def kill_fly(self, fly, sig=signal.SIGTERM):
        logger.info("%s: kill fly %s" % (self.name, fly.pid))
        fly.send_signal(sig)

    @util.debuglog
    def kill_flies(self, sig):
        for wid in self.flies.keys():
            try:
                fly = self.flies.pop(wid)
                self.kill_fly(fly, sig)
            except OSError, e:
                if e.errno != errno.ESRCH:
                    raise

    @util.debuglog
    def send_signal_child(self, wid, pid, signum):
        wid = int(wid)
        if wid in self.flies:
            fly = self.flies[wid]
            return fly.send_signal_child(int(pid), signum)
        else:
            return "error: fly not found"

    @util.debuglog
    def send_signal_children(self, wid, signum):
        wid = int(wid)
        if wid in self.flies:
            fly = self.flies[wid]
            return fly.send_signal_children(signum)
        else:
            return "error: fly not found"

    @util.debuglog
    def stop(self, graceful=True):
        self.stopped = True
        self.flapping.reset()

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

        logger.info('%s stopped' % self.name)

    @util.debuglog
    def start(self):
        if not self.stopped:
            return

        self.stopped = False
        self.reap_flies()
        self.manage_flies()
        logger.info('%s started' % self.name)

    @util.debuglog
    def restart(self):
        self.stop()
        self.start()
        logger.info('%s restarted' % self.name)

    @util.debuglog
    def reload(self):
        if self.prereload_fn is not None:
            self.prereload_fn(self)

        if self.send_hup:
            for wid, fly in self.flies.items():
                logger.info("SEND HUP to %s [%s]" % (wid, fly.pid))
                fly.send_signal(signal.SIGHUP)
        else:
            for i in range(self.numflies):
                self.spawn_fly()
            self.manage_flies()

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
            self.flapping.times = self.times = int(val)
            action = -1
        elif key == "within":
            self.flapping.within = self.within = float(val)
        elif key == "retry_in":
            self.flapping.retry_in = self.retry_in = float(val)
        elif key == "max_retry":
            self.flapping.max_retry = self.max_retry = int(val)
        elif key == "graceful_timeout":
            self.graceful_timeout = float(val)
            action = -1
        return action

    def do_action(self, num):
        self.stopped = False
        if num == 1:
            self.flapping.reset()
            for i in range(self.numflies):
                self.spawn_fly()
            self.manage_flies()
        else:
            self.reap_and_manage_flies()

    def get_opt(self, name):
        val = getattr(self, name)
        if name == "env":
            val = util.env_to_str(val)
        else:
            if val is None:
                val = ""
            else:
                val = str(val)
        return val

    #################
    # show commands #
    #################

    @util.debuglog
    def handle_set(self, *args):
        if len(args) < 2:
            return "error: invalid number of parameters"

        action = self.set_opt(args[0], " ".join(args[1:]))
        self.do_action(action)
        return "ok"

    @util.debuglog
    def handle_mset(self, *args):
        if len(args) < 2 or len(args) % 2 != 0:
            return "error: invalid number of parameters"
        action = 0
        rest = args
        while len(rest) > 0:
            kv, rest = rest[:2], rest[2:]
            new_action = self.set_opt(kv[0], kv[1])
            if new_action == 1:
                action = 1
        self.do_action(action)
        return "ok"

    @util.debuglog
    def handle_get(self, *args):
        if len(args) < 1:
            return "error: invalid number of parameters"

        if args[0] in self.optnames:
            return self.get_opt(args[0])
        else:
            return "error: %r option not found" % args[0]

    @util.debuglog
    def handle_mget(self, *args):
        if len(args) < 1:
            return "error: invalid number of parameters"

        ret = []
        for name in args:
            if name in self.optnames:
                val = self.get_opt(name)
                ret.append("%s: %s" % (name, val))
            else:
                return "error: %r option not found" % name
        return  "\n".join(ret)

    @util.debuglog
    def handle_options(self, *args):
        ret = []
        for name in self.optnames:
            val = self.get_opt(name)
            ret.append("%s: %s" % (name, val))
        return "\n".join(ret)

    @util.debuglog
    def handle_status(self, *args):
        if self.stopped:
            return "stopped"
        return "active"

    def handle_stop(self, *args):
        self.stop()
        return "ok"

    def handle_start(self, *args):
        self.start()
        return "ok"

    def handle_restart(self, *args):
        self.restart()
        return "ok"

    def handle_flies(self, *args):
        return ",".join([str(wid) for wid in self.flies.keys()])

    def handle_numflies(self, *args):
        return str(self.numflies)

    def handle_info(self, *args):
        if len(args) > 0:
            wid = int(args[0])
            if wid in self.flies:
                fly = self.flies[wid]
                return fly.info()
            else:
                return "error: fly '%s' not found" % wid
        else:
            return "\n".join([fly.info() for _, fly in self.flies.items()])

    @util.debuglog
    def handle_quit(self, *args):
        if len(args) > 0:
            wid = int(args[0])
            if wid in self.flies:
                try:
                    fly = self.flies.pop(wid)
                    self.kill_fly(fly)
                    return "ok"
                except OSError, e:
                    if e.errno != errno.ESRCH:
                        raise
            else:
                return "error: fly '%s' not found" % wid
        else:
            self.stop()
            return "ok"

    handle_kill = handle_stop = handle_quit

    @util.debuglog
    def handle_terminate(self, *args):
        if len(args) > 0:
            wid = int(args[0])
            if wid in self.flies:
                try:
                    fly = self.flies.pop(wid)
                    self.kill_fly(fly, signal.SIGTERM)
                    return "ok"
                except OSError, e:
                    if e.errno != errno.ESRCH:
                        raise
            else:
                return "error: fly '%s' not found" % wid
        else:
            self.stop(graceful=False)
            return "ok"

    def handle_reload(self, *args):
        self.reload()
        logger.info("%r reloaded" % self.name)
        return "ok"

    handle_hup = handle_reload

    def handle_ttin(self, *args):
        self.numflies += 1
        self.manage_flies()
        return str(self.numflies)

    def handle_ttou(self, *args):
        self.numflies -= 1
        self.manage_flies()
        return str(self.numflies)

    def handle_kill_child(self, wid, pid):
        return self.send_signal_child(wid, pid, signal.SIGKILL)

    def handle_quit_child(self, wid, pid):
        return self.send_signal_child(wid, pid, signal.SIGQUIT)

    def handle_children(self, wid):
        wid = int(wid)
        if wid in self.flies:
            fly = self.flies[wid]
            return fly.children()
        else:
            return "error: fly not found"

    @util.debuglog
    def handle_signal_fly(self, wid, sig):
        try:
            signum = getattr(signal, "SIG%s" % sig.upper())
        except AttributeError:
            return "error: unknown signal %s" % sig

        wid = int(wid)
        if wid in self.flies:
            fly = self.flies[wid]
            fly.send_signal(signum)
            return "ok"
        else:
            return "error: fly not found"

    def handle_kill_children(self, wid):
        return self.send_signal_children(wid, signal.SIGKILL)

    def handle_quit_children(self, wid):
        return self.send_signal_children(wid, signal.SIGQUIT)
