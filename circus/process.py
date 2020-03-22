try:
    import ctypes
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    ctypes = None       # NOQA
except ImportError:
    # Python on Solaris compiled with Sun Studio doesn't have ctypes
    ctypes = None       # NOQA

import sys
import errno
import os
from subprocess import PIPE
import time
import shlex
import warnings
try:
    import resource
except ImportError:
    resource = None     # NOQA

from psutil import (Popen, STATUS_ZOMBIE, STATUS_DEAD, NoSuchProcess,
                    AccessDenied)

from shlex import quote
from circus.sockets import CircusSocket
from circus.util import (get_info, to_uid, to_gid, debuglog, get_working_dir,
                         ObjectDict, replace_gnu_args, get_default_gid,
                         get_username_from_uid, IS_WINDOWS)
from circus import logger


_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


RUNNING = 0
DEAD_OR_ZOMBIE = 1
UNEXISTING = 2
OTHER = 3


# psutil < 2.x compat
def get_children(proc, recursive=False):
    try:
        return proc.children(recursive)
    except AttributeError:
        return proc.get_children(recursive)


def get_memory_info(proc):
    try:
        return proc.memory_info()
    except AttributeError:
        return proc.get_memory_info()


def get_cpu_percent(proc, **kw):
    try:
        return proc.cpu_percent(**kw)
    except AttributeError:
        return proc.get_cpu_percent(**kw)


def get_memory_percent(proc):
    try:
        return proc.memory_percent()
    except AttributeError:
        return proc.get_memory_percent()


def get_cpu_times(proc):
    try:
        return proc.cpu_times()
    except AttributeError:
        return proc.get_cpu_times()


def get_nice(proc):
    try:
        return proc.nice()
    except (AttributeError, TypeError):
        return proc.get_nice()


def get_cmdline(proc):
    try:
        return proc.cmdline()
    except TypeError:
        return proc.cmdline


def get_create_time(proc):
    try:
        return proc.create_time()
    except TypeError:
        return proc.create_time


def get_username(proc):
    try:
        return proc.username()
    except TypeError:
        return proc.username


def get_status(proc):
    try:
        return proc.status()
    except TypeError:
        return proc.status


class Process(object):
    """Wraps a process.

    Options:

    - **wid**: the process unique identifier. This value will be used to
      replace the *$WID* string in the command line if present.

    - **cmd**: the command to run. May contain any of the variables available
      that are being passed to this class. They will be replaced using the
      python format syntax.

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

    - **use_fds**: if True, will not close the fds in the subprocess. Must be
      be set to True on Windows if stdout or stderr are redirected.
      default: False.

    - **pipe_stdout**: if True, will open a PIPE on stdout. default: True.

    - **pipe_stderr**: if True, will open a PIPE on stderr. default: True.

    - **close_child_stdin**: If True, redirects the child process' stdin
      to /dev/null after the fork. default: True.

    - **close_child_stdout**: If True, redirects the child process' stdout
      to /dev/null after the fork. default: False.

    - **close_child_stderr**: If True, redirects the child process' stdout
      to /dev/null after the fork. default: False.
    """
    def __init__(self, name, wid, cmd, args=None, working_dir=None,
                 shell=False, uid=None, gid=None, env=None, rlimits=None,
                 executable=None, use_fds=False, watcher=None, spawn=True,
                 pipe_stdout=True, pipe_stderr=True, close_child_stdin=True,
                 close_child_stdout=False, close_child_stderr=False):

        self.name = name
        self.wid = wid
        self.cmd = cmd
        self.args = args
        self.working_dir = working_dir or get_working_dir()
        self.shell = shell
        if uid:
            self.uid = to_uid(uid)
            self.username = get_username_from_uid(self.uid)
        else:
            self.username = None
            self.uid = None
        self.gid = to_gid(gid) if gid else None
        self.env = env or {}
        self.rlimits = rlimits or {}
        self.executable = executable
        self.use_fds = use_fds
        self.watcher = watcher
        self.pipe_stdout = pipe_stdout
        self.pipe_stderr = pipe_stderr
        self.close_child_stdin = close_child_stdin
        self.close_child_stdout = close_child_stdout
        self.close_child_stderr = close_child_stderr
        self.stopping = False
        # sockets created before fork, should be let go after.
        self._sockets = []
        self._worker = None
        self.redirected = False
        self.started = 0

        if self.uid is not None and self.gid is None:
            self.gid = get_default_gid(self.uid)

        if IS_WINDOWS:
            if not self.use_fds and (self.pipe_stderr or self.pipe_stdout):
                raise ValueError("On Windows, you can't close the fds if "
                                 "you are redirecting stdout or stderr")

        if spawn:
            self.spawn()

    def _null_streams(self, streams):
        devnull = os.open(os.devnull, os.O_RDWR)
        try:
            for stream in streams:
                if not hasattr(stream, 'fileno'):
                    # we're probably dealing with a file-like
                    continue
                try:
                    stream.flush()
                    os.dup2(devnull, stream.fileno())
                except IOError:
                    # some streams, like stdin - might be already closed.
                    pass
        finally:
            os.close(devnull)

    def _get_sockets_fds(self):
        """Returns sockets dict. If this worker's cmd indicates use of
        a SO_REUSEPORT socket, a new socket is created and bound. This
        new socket's FD replaces original socket's FD in returned dict.
        This method populates `self._sockets` list. This list should be
        let go after `fork()`.
        """
        sockets_fds = None

        if self.watcher is not None and self.watcher.sockets is not None:
            sockets_fds = self.watcher._get_sockets_fds()
            reuseport_sockets = tuple((sn, s) for (sn, s)
                                      in self.watcher.sockets.items()
                                      if s.so_reuseport)

            for sn, s in reuseport_sockets:
                # watcher.cmd uses this reuseport socket
                if 'circus.sockets.%s' % sn in self.watcher.cmd:
                    sock = CircusSocket.load_from_config(s._cfg)
                    sock.bind_and_listen()
                    # replace original socket's fd
                    sockets_fds[sn] = sock.fileno()
                    # keep new socket until fork returns
                    self._sockets.append(sock)

        return sockets_fds

    def _get_stdin_socket_fd(self):
        if self.watcher is not None:
            return self.watcher._get_stdin_socket_fd()

    def spawn(self):
        self.started = time.time()
        sockets_fds = self._get_sockets_fds()

        args = self.format_args(sockets_fds=sockets_fds)

        def preexec():
            streams = []

            if self.close_child_stdin:
                streams.append(sys.stdin)

            if self.close_child_stdout:
                streams.append(sys.stdout)

            if self.close_child_stderr:
                streams.append(sys.stderr)

            self._null_streams(streams)
            os.setsid()

            if resource:
                for limit, value in self.rlimits.items():
                    res = getattr(
                        resource, 'RLIMIT_%s' % limit.upper(), None
                    )
                    if res is None:
                        raise ValueError('unknown rlimit "%s"' % limit)

                    # TODO(petef): support hard/soft limits

                    # for the NOFILE limit, if we fail to set an unlimited
                    # value then check the existing hard limit because we
                    # probably can't bypass it due to a kernel limit - so just
                    # assume that the caller means they want to use the kernel
                    # limit when they pass the unlimited value. This is better
                    # than failing to start the process and forcing the caller
                    # to always be aware of what the kernel configuration is.
                    # If they do pass in a real limit value, then we'll just
                    # raise the failure as they should know that their
                    # expectations couldn't be met.
                    # TODO - we can't log here as this occurs in the child
                    # process after the fork but it would be very good to
                    # notify the admin of the situation somehow.
                    retry = False
                    try:
                        resource.setrlimit(res, (value, value))
                    except ValueError:
                        if res == resource.RLIMIT_NOFILE and \
                                value == resource.RLIM_INFINITY:
                            _soft, value = resource.getrlimit(res)
                            retry = True
                        else:
                            raise
                    if retry:
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

                if self.username is not None:
                    try:
                        os.initgroups(self.username, self.gid)
                    except (OSError, AttributeError):
                        # not support on Mac or 2.6
                        pass

            if self.uid:
                os.setuid(self.uid)

            stdin_socket_fd = self._get_stdin_socket_fd()
            if stdin_socket_fd is not None:
                os.dup2(stdin_socket_fd, 0)

        if IS_WINDOWS:
            # On Windows we can't use a pre-exec function
            preexec_fn = None
        else:
            preexec_fn = preexec

        extra = {}
        if self.pipe_stdout:
            extra['stdout'] = PIPE

        if self.pipe_stderr:
            extra['stderr'] = PIPE

        self._worker = Popen(args, cwd=self.working_dir,
                             shell=self.shell, preexec_fn=preexec_fn,
                             env=self.env, close_fds=not self.use_fds,
                             executable=self.executable, **extra)

        # let go of sockets created only for self._worker to inherit
        self._sockets = []

    def format_args(self, sockets_fds=None):
        """ It's possible to use environment variables and some other variables
        that are available in this context, when spawning the processes.
        """
        logger.debug('cmd: ' + self.cmd)
        logger.debug('args: ' + str(self.args))

        current_env = ObjectDict(self.env.copy())

        format_kwargs = {
            'wid': self.wid, 'shell': self.shell, 'args': self.args,
            'env': current_env, 'working_dir': self.working_dir,
            'uid': self.uid, 'gid': self.gid, 'rlimits': self.rlimits,
            'executable': self.executable, 'use_fds': self.use_fds}

        if sockets_fds is not None:
            format_kwargs['sockets'] = sockets_fds

        if self.watcher is not None:
            for option in self.watcher.optnames:
                if option not in format_kwargs\
                        and hasattr(self.watcher, option):
                    format_kwargs[option] = getattr(self.watcher, option)

        cmd = replace_gnu_args(self.cmd, **format_kwargs)

        if '$WID' in cmd or (self.args and '$WID' in self.args):
            msg = "Using $WID in the command is deprecated. You should use "\
                  "the python string format instead. In your case, this "\
                  "means replacing the $WID in your command by $(WID)."

            warnings.warn(msg, DeprecationWarning)
            self.cmd = cmd.replace('$WID', str(self.wid))

        if self.args is not None:
            if isinstance(self.args, str):
                args = shlex.split(replace_gnu_args(
                    self.args, **format_kwargs))
            else:
                args = [replace_gnu_args(arg, **format_kwargs)
                        for arg in self.args]
            args = shlex.split(cmd, posix=not IS_WINDOWS) + args
        else:
            args = shlex.split(cmd, posix=not IS_WINDOWS)

        if self.shell:
            # subprocess.Popen(shell=True) implies that 1st arg is the
            # requested command, remaining args are applied to sh.
            args = [' '.join(quote(arg) for arg in args)]
            shell_args = format_kwargs.get('shell_args', None)
            if shell_args and IS_WINDOWS:
                logger.warn("shell_args won't apply for "
                            "windows platforms: %s", shell_args)
            elif isinstance(shell_args, str):
                args += shlex.split(replace_gnu_args(
                    shell_args, **format_kwargs))
            elif shell_args:
                args += [replace_gnu_args(arg, **format_kwargs)
                         for arg in shell_args]

        elif format_kwargs.get('shell_args', False):
            logger.warn("shell_args is defined but won't be used "
                        "in this context: %s", format_kwargs['shell_args'])
        logger.debug("process args: %s", args)
        return args

    def returncode(self):
        return self._worker.returncode

    @debuglog
    def poll(self):
        return self._worker.poll()

    @debuglog
    def is_alive(self):
        return self.poll() is None

    @debuglog
    def send_signal(self, sig):
        """Sends a signal **sig** to the process."""
        logger.debug("sending signal %s to %s" % (sig, self.pid))
        return self._worker.send_signal(sig)

    @debuglog
    def stop(self):
        """Stop the process and close stdout/stderr

        If the corresponding process is still here
        (normally it's already killed by the watcher),
        a SIGTERM is sent, then a SIGKILL after 1 second.

        The shutdown process (SIGTERM then SIGKILL) is
        normally taken by the watcher. So if the process
        is still there here, it's a kind of bad behavior
        because the graceful timeout won't be respected here.
        """
        try:
            try:
                if self.is_alive():
                    try:
                        return self._worker.terminate()
                    except AccessDenied:
                        # It can happen on Windows if the process
                        # dies after poll returns (unlikely)
                        pass
            finally:
                self.close_output_channels()
        except NoSuchProcess:
            pass

    def close_output_channels(self):
        if self._worker.stderr is not None:
            self._worker.stderr.close()
        if self._worker.stdout is not None:
            self._worker.stdout.close()

    def wait(self, timeout=None):
        """
        Wait for the process to terminate, in the fashion
        of waitpid.

        Accepts a timeout in seconds.
        """
        self._worker.wait(timeout)

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

        info["age"] = self.age()
        info["started"] = self.started
        info["children"] = []
        info['wid'] = self.wid
        for child in get_children(self._worker):
            info["children"].append(get_info(child))

        return info

    def children(self, recursive=False):
        """Return a list of children pids."""
        return [child.pid for child in get_children(self._worker, recursive)]

    def is_child(self, pid):
        """Return True is the given *pid* is a child of that process."""
        pids = [child.pid for child in get_children(self._worker)]
        if pid in pids:
            return True
        return False

    @debuglog
    def send_signal_child(self, pid, signum):
        """Send signal *signum* to child *pid*."""
        children = dict((child.pid, child)
                        for child in get_children(self._worker))
        try:
            children[pid].send_signal(signum)
        except KeyError:
            raise NoSuchProcess(pid)

    @debuglog
    def send_signal_children(self, signum, recursive=False):
        """Send signal *signum* to all children."""
        for child in get_children(self._worker, recursive):
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
        - UNEXISTING
        - OTHER
        """
        try:
            if get_status(self._worker) in (STATUS_ZOMBIE, STATUS_DEAD):
                return DEAD_OR_ZOMBIE
        except NoSuchProcess:
            return UNEXISTING

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

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        return self.started < other.started

    def __gt__(self, other):
        return self.started > other.started
