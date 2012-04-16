try:
    import ctypes
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    ctypes = None       # NOQA
except ImportError:
    # Python on Solaris compiled with Sun Studio doesn't have ctypes
    ctypes = None       # NOQA
import errno
import os
import resource
from subprocess import PIPE
import time
import shlex

from psutil import Popen, STATUS_ZOMBIE, STATUS_DEAD, NoSuchProcess

from circus.util import get_info, to_uid, to_gid, debuglog, get_working_dir
from circus import logger


_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


RUNNING = 0
DEAD_OR_ZOMBIE = 1
OTHER = 2


class Process(object):
    """Wraps a process.

    Options:

    - **wid**: the process unique identifier. This value will be used to
      replace the *$WID* string in the command line if present.

    - **cmd**: the command to run. May contain *$WID*, which will be
      replaced by **wid**.

    - **args**: the arguments for the command to run. Can be a list or
      a string. If **args** is  a string, it's splitted using
      :func:`shlex.split`. Defaults to None.

    - **executable**: When executable is given, the first item in
      the args sequence obtained from **cmd** is still treated by most
      programs as the command name, which can then be different from the
      actual executable name. It becomes the display name for the executing
      program in utilities such as **ps**.

    - **working_dir**: the working directory to run the command in. If
      not provided, will default to the current working directory.

    - **shell**: if *True*, will run the command in the shell
      environment. *False* by default. **warning: this is a
      security hazard**.

    - **uid**: if given, is the user id or name the command should run
      with. The current uid is the default.

    - **gid**: if given, is the group id or name the command should run
      with. The current gid is the default.

    - **env**: a mapping containing the environment variables the command
      will run with. Optional.

    - **rlimits**: a mapping containing rlimit names and values that will
      be set before the command runs.
    """
    def __init__(self, wid, cmd, args=None, working_dir=None, shell=False,
                 uid=None, gid=None, env=None, rlimits=None, executable=None):
        self.wid = wid
        if working_dir is None:
            self.working_dir = get_working_dir()
        else:
            self.working_dir = working_dir
        self.shell = shell
        self.env = env

        if rlimits is not None:
            self.rlimits = rlimits
        else:
            self.rlimits = {}

        self.cmd = cmd.replace('$WID', str(self.wid))
        if uid is None:
            self.uid = None
        else:
            self.uid = to_uid(uid)

        if gid is None:
            self.gid = None
        else:
            self.gid = to_gid(gid)

        def preexec_fn():
            os.setsid()

            for limit, value in self.rlimits.items():
                res = getattr(resource, 'RLIMIT_%s' % limit.upper(), None)
                if res is None:
                    raise ValueError('unknown rlimit "%s"' % limit)
                # TODO(petef): support hard/soft limits
                resource.setrlimit(res, (value, value))

            if self.gid:
                try:
                    os.setgid(self.gid)
                except OverflowError:
                    if not ctypes:
                        raise
                    # versions of python < 2.6.2 don't manage unsigned int for
                    # groups like on osx or fedora
                    os.setgid(-ctypes.c_int(-self.gid).value)

            if self.uid:
                os.setuid(self.uid)

        logger.debug('cmd: ' + cmd)
        logger.debug('args: ' + str(args))

        if args is not None:
            if isinstance(args, str):
                args_ = shlex.split(args)
            else:
                args_ = args[:]

            args_.insert(0, cmd)
        else:
            args_ = [cmd]

        logger.debug('Running %r' % ' '.join(args_))

        self._worker = Popen(args_, cwd=self.working_dir,
                             shell=self.shell, preexec_fn=preexec_fn,
                             env=self.env, close_fds=True, stdout=PIPE,
                             stderr=PIPE, executable=executable)

        self.started = time.time()

    @debuglog
    def poll(self):
        return self._worker.poll()

    @debuglog
    def send_signal(self, sig):
        """Sends a signal **sig** to the process."""
        return self._worker.send_signal(sig)

    @debuglog
    def stop(self):
        """Terminate the process."""
        try:
            if self._worker.poll() is None:
                return self._worker.terminate()
        finally:
            self._worker.stderr.close()
            self._worker.stdout.close()

    def age(self):
        """Return the age of the process in seconds."""
        return time.time() - self.started

    def info(self):
        """Return process info.

        The info returned is a mapping with these keys:

        - **mem_info1**: Resident Set Size Memory in bytes (RSS)
        - **mem_info2**: Virtual Memory Size in bytes (VMS).
        - **cpu**: % of cpu usage.
        - **mem**: % of memory usage.
        - **ctime**: process CPU (user + system) time in seconds.
        - **pid**: process id.
        - **username**: user name that owns the process.
        - **nice**: process niceness (between -20 and 20)
        - **cmdline**: the command line the process was run with.
        """
        try:
            info = get_info(self._worker)
        except NoSuchProcess:
            return "No such process (stopped?)"

        info["children"] = []
        for child in self._worker.get_children():
            info["children"].append(get_info(child))

        return info

    def children(self):
        """Return a list of children pids."""
        return [child.pid for child in self._worker.get_children()]

    def is_child(self, pid):
        """Return True is the given *pid* is a child of that process."""
        pids = [child.pid for child in self._worker.get_children()]
        if pid in pids:
            return True
        return False

    @debuglog
    def send_signal_child(self, pid, signum):
        """Send signal *signum* to child *pid*."""
        children = dict([(child.pid, child) \
                for child in self._worker.get_children()])

        children[pid].send_signal(signum)

    @debuglog
    def send_signal_children(self, signum):
        """Send signal *signum* to all children."""
        for child in self._worker.get_children():
            try:
                child.send_signal(signum)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    @property
    def status(self):
        """Return the process status as a constant

        - RUNNING
        - DEAD_OR_ZOMBIE
        - OTHER
        """
        try:
            if self._worker.status in (STATUS_ZOMBIE, STATUS_DEAD):
                return DEAD_OR_ZOMBIE
        except NoSuchProcess:
            return OTHER

        if self._worker.is_running():
            return RUNNING
        return OTHER

    @property
    def pid(self):
        """Return the *pid*"""
        return self._worker.pid

    @property
    def stdout(self):
        """Return the *stdout* stream"""
        return self._worker.stdout

    @property
    def stderr(self):
        """Return the *stdout* stream"""
        return self._worker.stderr
