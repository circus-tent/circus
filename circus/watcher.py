import copy
import errno
import os
import signal
import time
import sys
from random import randint

import site
from tornado import gen

from psutil import NoSuchProcess, TimeoutExpired
import zmq.utils.jsonapi as json
from tornado import ioloop

from circus.process import Process, DEAD_OR_ZOMBIE, UNEXISTING
from circus.papa_process_proxy import PapaProcessProxy
from circus import logger
from circus import util
from circus.stream import get_stream, Redirector
from circus.stream.papa_redirector import PapaRedirector
from circus.util import parse_env_dict, resolve_name, tornado_sleep, IS_WINDOWS
from circus.util import papa


class Watcher(object):

    """
    Class managing a list of processes for a given command.

    Options:

    - **name**: name given to the watcher. Used to uniquely identify it.

    - **cmd**: the command to run. May contain *$WID*, which will be
      replaced by **wid**.

    - **args**: the arguments for the command to run. Can be a list or
      a string. If **args** is  a string, it's splitted using
      :func:`shlex.split`. Defaults to None.

    - **numprocesses**: Number of processes to run.

    - **working_dir**: the working directory to run the command in. If
      not provided, will default to the current working directory.

    - **shell**: if *True*, will run the command in the shell
      environment. *False* by default. **warning: this is a
      security hazard**.

    - **uid**: if given, is the user id or name the command should run
      with. The current uid is the default.

    - **gid**: if given, is the group id or name the command should run
      with. The current gid is the default.

    - **send_hup**: if True, a process reload will be done by sending
      the SIGHUP signal. Defaults to False.

    - **stop_signal**: the signal to send when stopping the process.
      Defaults to SIGTERM.

    - **stop_children**: send the **stop_signal** to the children too.
      Defaults to False.

    - **env**: a mapping containing the environment variables the command
      will run with. Optional.

    - **rlimits**: a mapping containing rlimit names and values that will
      be set before the command runs.

    - **stdout_stream**: a mapping that defines the stream for
      the process stdout. Defaults to None.

      Optional. When provided, *stdout_stream* is a mapping containing up to
      three keys:

      - **class**: the stream class. Defaults to
        `circus.stream.FileStream`
      - **filename**: the filename, if using a FileStream
      - **max_bytes**: maximum file size, after which a new output file is
        opened. defaults to 0 which means no maximum size (only applicable
        with FileStream).
      - **backup_count**: how many backups to retain when rotating files
        according to the max_bytes parameter. defaults to 0 which means
        no backups are made (only applicable with FileStream)

      This mapping will be used to create a stream callable of the specified
      class.
      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

      This is not supported on Windows.

    - **stderr_stream**: a mapping that defines the stream for
      the process stderr. Defaults to None.

      Optional. When provided, *stderr_stream* is a mapping containing up to
      three keys:
      - **class**: the stream class. Defaults to `circus.stream.FileStream`
      - **filename**: the filename, if using a FileStream
      - **max_bytes**: maximum file size, after which a new output file is
        opened. defaults to 0 which means no maximum size (only applicable
        with FileStream)
      - **backup_count**: how many backups to retain when rotating files
        according to the max_bytes parameter. defaults to 0 which means
        no backups are made (only applicable with FileStream).

      This mapping will be used to create a stream callable of the specified
      class.

      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

      This is not supported on Windows.

    - **priority** -- integer that defines a priority for the watcher. When
      the Arbiter do some operations on all watchers, it will sort them
      with this field, from the bigger number to the smallest.
      (default: 0)

    - **singleton** -- If True, this watcher has a single process.
      (default:False)

    - **use_sockets** -- If True, the processes will inherit the file
      descriptors, thus can reuse the sockets opened by circusd.
      (default: False)

    - **on_demand** -- If True, the processes will be started only
      at the first connection to the socket
      (default: False)

    - **copy_env** -- If True, the environment in which circus is running
      run will be reproduced for the workers. This defaults to True on
      Windows as you cannot run any executable without the **SYSTEMROOT**
      variable. (default: False)

    - **copy_path** -- If True, circusd *sys.path* is sent to the
      process through *PYTHONPATH*. You must activate **copy_env** for
      **copy_path** to work. (default: False)

    - **max_age**: If set after around max_age seconds, the process is
      replaced with a new one.  (default: 0, Disabled)

    - **max_age_variance**: The maximum number of seconds that can be added to
      max_age. This extra value is to avoid restarting all processes at the
      same time.  A process will live between max_age and
      max_age + max_age_variance seconds.

    - **hooks**: callback functions for hooking into the watcher startup
      and shutdown process. **hooks** is a dict where each key is the hook
      name and each value is a 2-tuple with the name of the callable
      or the callable itself and a boolean flag indicating if an
      exception occuring in the hook should not be ignored.
      Possible values for the hook name: *before_start*, *after_start*,
      *before_spawn*, *after_spawn*, *before_stop*, *after_stop*.,
      *before_signal*, *after_signal* or *extended_stats*.

    - **options** -- extra options for the worker. All options
      found in the configuration file for instance, are passed
      in this mapping -- this can be used by plugins for watcher-specific
      options.

    - **respawn** -- If set to False, the processes handled by a watcher will
      not be respawned automatically. (default: True)

    - **virtualenv** -- The root directory of a virtualenv. If provided, the
      watcher will load the environment for its execution. (default: None)

    - **stdin_socket**: If not None, the socket with matching name is placed
      at file descriptor 0 (stdin) of the processes.
      default: None.

    - **close_child_stdin**: If True, closes the stdin after the fork.
      default: True.

    - **close_child_stdout**: If True, closes the stdout after the fork.
      default: False.

    - **close_child_stderr**: If True, closes the stderr after the fork.
      default: False.

    - **use_papa**: If True, use the papa process kernel for this process.
      default: False.
    """

    def __init__(self, name, cmd, args=None, numprocesses=1, warmup_delay=0.,
                 working_dir=None, shell=False, shell_args=None, uid=None,
                 max_retry=5, gid=None, send_hup=False,
                 stop_signal=signal.SIGTERM, stop_children=False, env=None,
                 graceful_timeout=30.0, prereload_fn=None, rlimits=None,
                 executable=None, stdout_stream=None, stderr_stream=None,
                 priority=0, loop=None, singleton=False, use_sockets=False,
                 copy_env=False, copy_path=False, max_age=0,
                 max_age_variance=30, hooks=None, respawn=True,
                 autostart=True, on_demand=False, virtualenv=None,
                 stdin_socket=None, close_child_stdin=True,
                 close_child_stdout=False,
                 close_child_stderr=False, virtualenv_py_ver=None,
                 use_papa=False, **options):
        self.name = name
        self.use_sockets = use_sockets
        self.on_demand = on_demand
        self.res_name = name.lower().replace(" ", "_")
        self.numprocesses = int(numprocesses)
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self.args = args
        self._status = "stopped"
        self.graceful_timeout = float(graceful_timeout)
        self.prereload_fn = prereload_fn
        self.executable = None
        self.priority = priority
        self.stdout_stream_conf = copy.copy(stdout_stream)
        self.stderr_stream_conf = copy.copy(stderr_stream)
        self.stdout_stream = get_stream(self.stdout_stream_conf)
        self.stderr_stream = get_stream(self.stderr_stream_conf)
        self.stream_redirector = None
        self.max_retry = int(max_retry)
        self._options = options
        self.singleton = singleton
        self.copy_env = copy_env
        self.copy_path = copy_path
        self.virtualenv = virtualenv
        self.virtualenv_py_ver = virtualenv_py_ver
        self.max_age = int(max_age)
        self.max_age_variance = int(max_age_variance)
        self.ignore_hook_failure = ['before_stop', 'after_stop',
                                    'before_signal', 'after_signal',
                                    'extended_stats']

        self.respawn = respawn
        self.autostart = autostart
        self.stdin_socket = stdin_socket
        self.close_child_stdin = close_child_stdin
        self.close_child_stdout = close_child_stdout
        self.close_child_stderr = close_child_stderr
        self.use_papa = use_papa and papa is not None
        self.loop = loop or ioloop.IOLoop.current()

        if singleton and self.numprocesses not in (0, 1):
            raise ValueError("Cannot have %d processes with a singleton "
                             " watcher" % self.numprocesses)

        if IS_WINDOWS:
            if self.stdout_stream or self.stderr_stream:
                raise NotImplementedError("Streams are not supported"
                                          " on Windows.")

            if not copy_env and not env:
                # Copy the env by default on Windows as we can't run any
                # executable without some env variables
                # Eventually, we could set only some required variables,
                # such as SystemRoot
                self.copy_env = True

        self.optnames = (("numprocesses", "warmup_delay", "working_dir",
                          "uid", "gid", "send_hup", "stop_signal",
                          "stop_children", "shell", "shell_args",
                          "env", "max_retry", "cmd", "args", "respawn",
                          "graceful_timeout", "executable", "use_sockets",
                          "priority", "copy_env", "singleton",
                          "stdout_stream_conf", "on_demand",
                          "stderr_stream_conf", "max_age", "max_age_variance",
                          "close_child_stdin", "close_child_stdout",
                          "close_child_stderr", "use_papa") +
                         tuple(options.keys()))

        if not working_dir:
            # working dir hasn't been set
            working_dir = util.get_working_dir()

        self.working_dir = working_dir
        self.processes = {}
        self.shell = shell
        self.shell_args = shell_args
        self.uid = uid
        self.gid = gid

        if self.copy_env:
            self.env = os.environ.copy()
            if self.copy_path:
                path = os.pathsep.join(sys.path)
                self.env['PYTHONPATH'] = path
            if env is not None:
                self.env.update(env)
        else:
            if self.copy_path:
                raise ValueError(('copy_env and copy_path must have the '
                                  'same value'))
            self.env = env

        if self.virtualenv:
            util.load_virtualenv(self, py_ver=virtualenv_py_ver)

        # load directories in PYTHONPATH if provided
        # so if a hook is there, it can be loaded
        if self.env is not None and 'PYTHONPATH' in self.env:
            for path in self.env['PYTHONPATH'].split(os.pathsep):
                if path in sys.path:
                    continue
                site.addsitedir(path)

        self.rlimits = rlimits
        self.send_hup = send_hup
        self.stop_signal = stop_signal
        self.stop_children = stop_children
        self.sockets = self.evpub_socket = None
        self.arbiter = None
        self.hooks = {}
        self._resolve_hooks(hooks)
        self._found_wids = []

        if self.use_papa:
            with papa.Papa() as p:
                base_name = 'circus.{0}.*'.format(name.lower())
                running = p.list_processes(base_name)
                self._found_wids = [int(proc_name[len(base_name) - 1:])
                                    for proc_name in running]

    def _reload_hook(self, key, hook, ignore_error):
        hook_name = key.split('.')[-1]
        self._resolve_hook(hook_name, hook, ignore_error, reload_module=True)

    @property
    def _redirector_class(self):
        return PapaRedirector if self.use_papa else Redirector

    @property
    def _process_class(self):
        return PapaProcessProxy if self.use_papa else Process

    def _reload_stream(self, key, val):
        parts = key.split('.', 1)

        stream_type = 'stdout' if parts[0] == 'stdout_stream' else 'stderr'
        old_stream = self.stream_redirector.get_stream(stream_type) if\
            self.stream_redirector else None
        if stream_type == 'stdout':
            self.stdout_stream_conf[parts[1]] = val
            new_stream = get_stream(self.stdout_stream_conf, reload=True)
            self.stdout_stream = new_stream
        else:
            self.stderr_stream_conf[parts[1]] = val
            new_stream = get_stream(self.stderr_stream_conf, reload=True)
            self.stderr_stream = new_stream

        if self.stream_redirector:
            self.stream_redirector.change_stream(stream_type, new_stream)
        else:
            self.stream_redirector = self._redirector_class(
                self.stdout_stream, self.stderr_stream, loop=self.loop)

        if old_stream:
            if hasattr(old_stream, 'close'):
                old_stream.close()
            return 0

        self.stream_redirector.start()
        return 1

    def _create_redirectors(self):
        if self.stdout_stream or self.stderr_stream:
            if self.stream_redirector:
                self.stream_redirector.stop()
            self.stream_redirector = self._redirector_class(
                self.stdout_stream, self.stderr_stream, loop=self.loop)
        else:
            self.stream_redirector = None

    def _resolve_hook(self, name, callable_or_name, ignore_failure,
                      reload_module=False):
        if callable(callable_or_name):
            self.hooks[name] = callable_or_name
        else:
            # will raise ImportError on failure
            self.hooks[name] = resolve_name(callable_or_name,
                                            reload=reload_module)

        if ignore_failure:
            self.ignore_hook_failure.append(name)

    def _resolve_hooks(self, hooks):
        """Check the supplied hooks argument to make sure we can find
        callables"""
        if hooks is None:
            return
        for name, (callable_or_name, ignore_failure) in hooks.items():
            self._resolve_hook(name, callable_or_name, ignore_failure)

    @property
    def pending_socket_event(self):
        return self.on_demand and not self.arbiter.socket_event

    @classmethod
    def load_from_config(cls, config):
        if 'env' in config:
            config['env'] = parse_env_dict(config['env'])
        cfg = config.copy()

        w = cls(name=config.pop('name'), cmd=config.pop('cmd'), **config)
        w._cfg = cfg

        return w

    @util.debuglog
    def initialize(self, evpub_socket, sockets, arbiter):
        self.evpub_socket = evpub_socket
        self.sockets = sockets
        self.arbiter = arbiter

    def __len__(self):
        return len(self.processes)

    def __repr__(self):
        return "<circus.Watcher name=%s numprocesses=%s>" % (self.name,
                                                             self.numprocesses)

    def notify_event(self, topic, msg):
        """Publish a message on the event publisher channel"""

        name = self.res_name

        multipart_msg = [
            ("watcher.%s.%s" % (name, topic)).encode('utf8'), json.dumps(msg)
        ]

        if self.evpub_socket is not None and not self.evpub_socket.closed:
            self.evpub_socket.send_multipart(multipart_msg)

    @util.debuglog
    def reap_process(self, pid, status=None):
        """ensure that the process is killed (and not a zombie)"""
        if pid not in self.processes:
            return

        # We ignore the hook result
        self.call_hook("before_reap", process_pid=pid, time=time.time())

        process = self.processes.pop(pid)

        timeout = 0.001

        while status is None:
            if IS_WINDOWS:
                try:
                    # On Windows we can't use waitpid as it's blocking,
                    # so we use psutils' wait
                    status = process.wait(timeout=timeout)
                except TimeoutExpired:
                    continue
            else:
                try:
                    resulting_pid, status = os.waitpid(pid, os.WNOHANG)
                    if (resulting_pid, status) == (0, 0):
                        status = None
                        time.sleep(timeout)
                        continue
                except OSError as e:
                    if e.errno == errno.ECHILD:
                        status = None
                    else:
                        raise

            if status is None:
                # nothing to do here, we do not have any child
                # process running
                # but we still need to send the "reap" signal.
                #
                # This can happen if poll() or wait() were called on
                # the underlying process.
                logger.debug('reaping already dead process %s [%s]',
                             pid, self.name)
                msg = {"process_pid": pid,
                       "time": time.time(),
                       "exit_code": process.returncode()}
                self.notify_event("reap", msg)
                process.stop()
                # We ignore the hook result
                self.call_hook("after_reap", process_status=None, **msg)
                return

        # get return code
        if hasattr(os, 'WIFSIGNALED'):
            exit_code = 0

            if os.WIFSIGNALED(status):
                # The Python Popen object returns <-signal> in it's returncode
                # property if the process exited on a signal, so emulate that
                # behavior here so that pubsub clients watching for reap can
                # distinguish between an exit with a non-zero exit code and
                # a signal'd exit. This is also consistent with the notify
                # event reap message above that uses the returncode function
                # (that ends up calling Popen.returncode)
                exit_code = -os.WTERMSIG(status)
            # process exited using exit(2) system call; return the
            # integer exit(2) system call has been called with
            elif os.WIFEXITED(status):
                exit_code = os.WEXITSTATUS(status)
            else:
                # should never happen
                raise RuntimeError("Unknown process exit status")
        else:
            # On Windows we don't have such distinction
            exit_code = status

        # if the process is dead or a zombie try to definitely stop it.
        process_status = process.status
        if process_status in (DEAD_OR_ZOMBIE, UNEXISTING):
            process.stop()

        logger.debug('reaping process %s [%s]', pid, self.name)
        msg = {"process_pid": pid,
               "time": time.time(),
               "exit_code": exit_code}
        self.notify_event("reap", msg)
        # We ignore the hook result
        self.call_hook("after_reap", process_status=process_status, **msg)

    @util.debuglog
    def reap_processes(self):
        """Reap all the processes for this watcher.
        """
        if self.is_stopped():
            logger.debug('do not reap processes as the watcher is stopped')
            return

        # reap_process changes our dict, look through the copy of keys
        for pid in list(self.processes.keys()):
            self.reap_process(pid)

    @gen.coroutine
    @util.debuglog
    def manage_processes(self):
        """Manage processes."""
        if self.is_stopped():
            return

        # remove dead or zombie processes first
        for process in list(self.processes.values()):
            if process.status in (DEAD_OR_ZOMBIE, UNEXISTING):
                self.processes.pop(process.pid)

        if self.max_age:
            yield self.remove_expired_processes()

        # adding fresh processes
        if len(self.processes) < self.numprocesses and not self.is_stopping():
            if self.respawn:
                yield self.spawn_processes()
            elif not len(self.processes) and not self.on_demand:
                yield self._stop()

        # removing extra processes
        if len(self.processes) > self.numprocesses:
            processes_to_kill = []
            for process in sorted(self.processes.values(),
                                  key=lambda process: process.started,
                                  reverse=True)[self.numprocesses:]:
                if process.status in (DEAD_OR_ZOMBIE, UNEXISTING):
                    self.processes.pop(process.pid)
                else:
                    processes_to_kill.append(process)

            removes = yield [self.kill_process(process)
                             for process in processes_to_kill]
            for i, process in enumerate(processes_to_kill):
                if removes[i]:
                    self.processes.pop(process.pid)

    @gen.coroutine
    @util.debuglog
    def remove_expired_processes(self):
        expired_processes = [p for p in self.processes.values()
                             if p.age() > (self.max_age + randint(0,
                                           self.max_age_variance))]
        removes = yield [self.kill_process(x) for x in expired_processes]
        for i, process in enumerate(expired_processes):
            if removes[i]:
                self.processes.pop(process.pid)

    @gen.coroutine
    @util.debuglog
    def reap_and_manage_processes(self):
        """Reap & manage processes."""
        if self.is_stopped():
            return
        self.reap_processes()
        yield self.manage_processes()

    @gen.coroutine
    @util.debuglog
    def spawn_processes(self):
        """Spawn processes.
        """
        # when an on_demand process dies, do not restart it until
        # the next event
        if self.pending_socket_event:
            self._status = "stopped"
            return
        for i in self._found_wids:
            self.spawn_process(i)
            yield tornado_sleep(0)
        self._found_wids = {}

        for i in range(self.numprocesses - len(self.processes)):
            res = self.spawn_process()
            if res is False:
                yield self._stop()
                break
            delay = self.warmup_delay
            if isinstance(res, float):
                delay -= (time.time() - res)
                if delay < 0:
                    delay = 0
            yield tornado_sleep(delay)

    def _get_sockets_fds(self):
        # XXX should be cached
        if self.sockets is None:
            return {}
        return dict((name, sock.fileno())
                    for name, sock in self.sockets.items()
                    if sock.use_papa == self.use_papa)

    def _get_stdin_socket_fd(self):
        if self.stdin_socket is not None:
            if self.stdin_socket not in self.sockets:
                raise Exception("stdin_socket '%s' does not exist" %
                                self.stdin_socket)
            return self.sockets[self.stdin_socket].fileno()

    def spawn_process(self, recovery_wid=None):
        """Spawn process.

        Return True if ok, False if the watcher must be stopped
        """
        if self.is_stopped():
            return True

        if not recovery_wid and not self.call_hook('before_spawn'):
            return False

        cmd = util.replace_gnu_args(self.cmd, env=self.env)
        nb_tries = 0

        # start the redirector now so we can catch any startup errors
        if self.stream_redirector:
            self.stream_redirector.start()

        while nb_tries < self.max_retry or self.max_retry == -1:
            process = None
            pipe_stdout = self.stdout_stream is not None
            pipe_stderr = self.stderr_stream is not None

            # noinspection PyPep8Naming
            ProcCls = self._process_class
            try:
                process = ProcCls(self.name, recovery_wid or self._nextwid,
                                  cmd, args=self.args,
                                  working_dir=self.working_dir,
                                  shell=self.shell, uid=self.uid, gid=self.gid,
                                  env=self.env, rlimits=self.rlimits,
                                  executable=self.executable,
                                  use_fds=self.use_sockets, watcher=self,
                                  pipe_stdout=pipe_stdout,
                                  pipe_stderr=pipe_stderr,
                                  close_child_stdin=self.close_child_stdin,
                                  close_child_stdout=self.close_child_stdout,
                                  close_child_stderr=self.close_child_stderr)

                # stream stderr/stdout if configured
                if self.stream_redirector:
                    self.stream_redirector.add_redirections(process)

                self.processes[process.pid] = process
                logger.debug('running %s process [pid %d]', self.name,
                             process.pid)
                if not self.call_hook('after_spawn', pid=process.pid):
                    self.kill_process(process)
                    del self.processes[process.pid]
                    return False

            # catch ValueError as well, as a misconfigured rlimit setting could
            # lead to bad infinite retries here
            except (OSError, ValueError) as e:
                logger.warning('error in %r: %s', self.name, str(e))

            if process is None:
                nb_tries += 1
                continue
            else:
                self.notify_event("spawn", {"process_pid": process.pid,
                                            "time": process.started})
                return process.started
        return False

    @util.debuglog
    def send_signal_process(self, process, signum, recursive=False):
        """Send the signum signal to the process

        The signal is sent to the process itself then to all the children
        """
        children = None
        try:
            # getting the process children
            children = process.children(recursive=recursive)

            # sending the signal to the process itself
            self.send_signal(process.pid, signum)
            self.notify_event("kill", {"process_pid": process.pid,
                                       "time": time.time()})
        except NoSuchProcess:
            # already dead !
            if children is None:
                return

        # now sending the same signal to all the children
        for child_pid in children:
            try:
                process.send_signal_child(child_pid, signum)
                self.notify_event("kill", {"process_pid": child_pid,
                                  "time": time.time()})
            except NoSuchProcess:
                # already dead !
                pass

    @gen.coroutine
    @util.debuglog
    def kill_process(self, process, stop_signal=None, graceful_timeout=None):
        """Kill process (stop_signal, graceful_timeout then SIGKILL)
        """
        if stop_signal is None:
            stop_signal = self.stop_signal
        if graceful_timeout is None:
            graceful_timeout = self.graceful_timeout

        if process.stopping:
            raise gen.Return(False)
        try:
            logger.debug("%s: kill process %s", self.name, process.pid)
            if self.stop_children:
                self.send_signal_process(process, stop_signal)
            else:
                self.send_signal(process.pid, stop_signal)
                self.notify_event("kill", {"process_pid": process.pid,
                                           "time": time.time()})
        except NoSuchProcess:
            raise gen.Return(False)

        process.stopping = True
        waited = 0
        while waited < graceful_timeout:
            if not process.is_alive():
                break
            yield tornado_sleep(0.1)
            waited += 0.1
        if waited >= graceful_timeout:
            # On Windows we can't send a SIGKILL signal, but the
            # process.stop function will terminate the process
            # later anyway
            if hasattr(signal, 'SIGKILL'):
                # We are not smart anymore
                self.send_signal_process(process, signal.SIGKILL,
                                         recursive=True)
        if self.stream_redirector:
            self.stream_redirector.remove_redirections(process)
        process.stopping = False
        process.stop()
        raise gen.Return(True)

    @gen.coroutine
    @util.debuglog
    def kill_processes(self, stop_signal=None, graceful_timeout=None):
        """Kill all processes (stop_signal, graceful_timeout then SIGKILL)
        """
        active_processes = self.get_active_processes()
        try:
            yield [self.kill_process(process,
                                     stop_signal=stop_signal,
                                     graceful_timeout=graceful_timeout)
                   for process in active_processes]
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise

    @util.debuglog
    def send_signal(self, pid, signum):
        is_sigkill = hasattr(signal, 'SIGKILL') and signum == signal.SIGKILL
        if pid in self.processes:
            process = self.processes[pid]
            hook_result = self.call_hook("before_signal",
                                         pid=pid, signum=signum)
            if not is_sigkill and not hook_result:
                logger.debug("before_signal hook didn't return True "
                             "=> signal %i is not sent to %i" % (signum, pid))
            else:
                process.send_signal(signum)
            self.call_hook("after_signal", pid=pid, signum=signum)
        else:
            logger.debug('process %s does not exist' % pid)

    @util.debuglog
    def send_signal_child(self, pid, child_id, signum):
        """Send signal to a child.
        """
        process = self.processes[pid]
        try:
            process.send_signal_child(int(child_id), signum)
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise

    @util.debuglog
    def send_signal_children(self, pid, signum, recursive=False):
        """Send signal to all children.
        """
        process = self.processes[int(pid)]
        process.send_signal_children(signum, recursive)

    @util.debuglog
    def status(self):
        return self._status

    @util.debuglog
    def process_info(self, pid, extended=False):
        process = self.processes[int(pid)]
        result = process.info()
        if extended and 'extended_stats' in self.hooks:
            self.hooks['extended_stats'](self, self.arbiter,
                                         'extended_stats',
                                         pid=pid, stats=result)
        return result

    @util.debuglog
    def info(self, extended=False):
        result = dict([(proc.pid, proc.info())
                       for proc in self.processes.values()])
        if extended and 'extended_stats' in self.hooks:
            for pid, stats in result.items():
                self.hooks['extended_stats'](self, self.arbiter,
                                             'extended_stats',
                                             pid=pid, stats=stats)
        return result

    @util.synchronized("watcher_stop")
    @gen.coroutine
    def stop(self):
        # stop streams too since we are stopping the watcher completely
        yield self._stop(True)

    @util.debuglog
    @gen.coroutine
    def _stop(self, close_output_streams=False, for_shutdown=False):
        if self.is_stopped():
            return
        self._status = "stopping"
        skip = for_shutdown and self.use_papa
        if not skip:
            logger.debug('stopping the %s watcher' % self.name)
            logger.debug('gracefully stopping processes [%s] for %ss' % (
                         self.name, self.graceful_timeout))
            # We ignore the hook result
            self.call_hook('before_stop')
            yield self.kill_processes()
            self.reap_processes()

        # stop redirectors
        if self.stream_redirector:
            self.stream_redirector.stop()
            self.stream_redirector = None
        if close_output_streams:
            if self.stdout_stream and hasattr(self.stdout_stream, 'close'):
                self.stdout_stream.close()
            if self.stderr_stream and hasattr(self.stderr_stream, 'close'):
                self.stderr_stream.close()
        # notify about the stop
        if skip:
            logger.info('%s left running in papa', self.name)
        else:
            if self.evpub_socket is not None:
                self.notify_event("stop", {"time": time.time()})
            self._status = "stopped"
            # We ignore the hook result
            self.call_hook('after_stop')
            logger.info('%s stopped', self.name)

    def get_active_processes(self):
        """return a list of pids of active processes (not already stopped)"""
        return [p for p in self.processes.values()
                if p.status not in (DEAD_OR_ZOMBIE, UNEXISTING)]

    def get_active_pids(self):
        """return a list of pids of active processes (not already stopped)"""
        return [p.pid for p in self.processes.values()
                if p.status not in (DEAD_OR_ZOMBIE, UNEXISTING)]

    @property
    def pids(self):
        """Returns a list of PIDs"""
        return [process.pid for process in self.processes]

    @property
    def _nextwid(self):
        used_wids = set([p.wid for p in self.processes.values()])
        all_wids = set(range(1, self.numprocesses * 2 + 1))
        available_wids = sorted(all_wids - used_wids)
        try:
            return available_wids[0]
        except IndexError:
            raise RuntimeError("Process count > numproceses*2")

    def call_hook(self, hook_name, **kwargs):
        """Call a hook function"""
        hook_kwargs = {'watcher': self, 'arbiter': self.arbiter,
                       'hook_name': hook_name}
        hook_kwargs.update(kwargs)
        if hook_name in self.hooks:
            try:
                result = self.hooks[hook_name](**hook_kwargs)
                self.notify_event("hook_success",
                                  {"name": hook_name, "time": time.time()})
            except Exception as error:
                logger.exception('Hook %r failed' % hook_name)
                result = hook_name in self.ignore_hook_failure
                self.notify_event("hook_failure",
                                  {"name": hook_name, "time": time.time(),
                                   "error": str(error)})

            return result
        else:
            return True

    @util.synchronized("watcher_start")
    @gen.coroutine
    def start(self):
        before_pids = set() if self.is_stopped() else set(self.processes)
        yield self._start()
        after_pids = set(self.processes)
        raise gen.Return({'started': sorted(after_pids - before_pids),
                          'kept': sorted(after_pids & before_pids)})

    @gen.coroutine
    @util.debuglog
    def _start(self):
        """Start.
        """
        if self.pending_socket_event:
            return

        if not self.is_stopped():
            if len(self.processes) < self.numprocesses:
                self.reap_processes()
                yield self.spawn_processes()
            return

        found_wids = len(self._found_wids)
        if not self._found_wids and not self.call_hook('before_start'):
            logger.debug('Aborting startup')
            return

        self._status = "starting"

        if self.stdout_stream and hasattr(self.stdout_stream, 'open'):
            self.stdout_stream.open()
        if self.stderr_stream and hasattr(self.stderr_stream, 'open'):
            self.stderr_stream.open()

        self._create_redirectors()
        self.reap_processes()
        yield self.spawn_processes()

        # If not self.processes, the before_spawn or after_spawn hooks have
        # probably prevented startup so give up
        if not self.processes or not self.call_hook('after_start'):
            logger.debug('Aborting startup')
            # stop streams too since we are bailing on this watcher completely
            yield self._stop(True)
            return

        self._status = "active"
        if found_wids:
            logger.info('%s already running' % self.name)
        else:
            logger.info('%s started' % self.name)
        self.notify_event("start", {"time": time.time()})

    @util.synchronized("watcher_restart")
    @gen.coroutine
    def restart(self):
        before_pids = set() if self.is_stopped() else set(self.processes)
        yield self._restart()
        after_pids = set(self.processes)
        raise gen.Return({'stopped': sorted(before_pids - after_pids),
                          'started': sorted(after_pids - before_pids),
                          'kept': sorted(after_pids & before_pids)})

    @gen.coroutine
    @util.debuglog
    def _restart(self):
        yield self._stop()
        yield self._start()

    @util.synchronized("watcher_reload")
    @gen.coroutine
    def reload(self, graceful=True, sequential=False):
        before_pids = set() if self.is_stopped() else set(self.processes)
        yield self._reload(graceful=graceful, sequential=sequential)
        after_pids = set(self.processes)
        raise gen.Return({'stopped': sorted(before_pids - after_pids),
                          'started': sorted(after_pids - before_pids),
                          'kept': sorted(after_pids & before_pids)})

    @gen.coroutine
    @util.debuglog
    def _reload(self, graceful=True, sequential=False):
        """ reload
        """
        if not graceful and sequential:
            logger.warn("with graceful=False, sequential=True is ignored")
        if self.prereload_fn is not None:
            self.prereload_fn(self)

        if not graceful:
            yield self._restart()
            return

        if self.is_stopped():
            yield self._start()
        elif self.send_hup:
            for process in self.processes.values():
                logger.info("SENDING HUP to %s" % process.pid)
                process.send_signal(signal.SIGHUP)
        else:
            if sequential:
                active_processes = self.get_active_processes()
                for process in active_processes:
                    yield self.kill_process(process)
                    self.reap_process(process.pid)
                    self.spawn_process()
                    yield tornado_sleep(self.warmup_delay)
            else:
                for i in range(self.numprocesses):
                    self.spawn_process()
                yield self.manage_processes()
        self.notify_event("reload", {"time": time.time()})
        logger.info('%s reloaded', self.name)

    @gen.coroutine
    def set_numprocesses(self, np):
        if np < 0:
            np = 0
        if self.singleton and np > 1:
            raise ValueError('Singleton watcher has a single process')
        self.numprocesses = np
        yield self.manage_processes()
        raise gen.Return(self.numprocesses)

    @util.synchronized("watcher_incr")
    @gen.coroutine
    @util.debuglog
    def incr(self, nb=1):
        res = yield self.set_numprocesses(self.numprocesses + nb)
        raise gen.Return(res)

    @util.synchronized("watcher_decr")
    @gen.coroutine
    @util.debuglog
    def decr(self, nb=1):
        res = yield self.set_numprocesses(self.numprocesses - nb)
        raise gen.Return(res)

    @util.synchronized("watcher_set_opt")
    def set_opt(self, key, val):
        """Set a watcher option.

        This function set the watcher options. unknown keys are ignored.
        This function return an action number:

        - 0: trigger the process management
        - 1: trigger a graceful reload of the processes;
        """
        action = 0

        if key in self._options:
            self._options[key] = val
            action = -1    # XXX for now does not trigger a reload
        elif key == "numprocesses":
            val = int(val)
            if val < 0:
                val = 0
            if self.singleton and val > 1:
                raise ValueError('Singleton watcher has a single process')
            self.numprocesses = val
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
        elif key == "stop_signal":
            self.stop_signal = util.to_signum(val)
        elif key == "stop_children":
            self.stop_children = util.to_bool(val)
        elif key == "shell":
            self.shell = val
            action = 1
        elif key == "env":
            self.env = val
            action = 1
        elif key == "cmd":
            self.cmd = val
            action = 1
        elif key == "args":
            self.args = val
            action = 1
        elif key == "graceful_timeout":
            self.graceful_timeout = float(val)
            action = -1
        elif key == "max_age":
            self.max_age = int(val)
            action = 1
        elif key == "max_age_variance":
            self.max_age_variance = int(val)
            action = 1
        elif (key.startswith('stdout_stream') or
              key.startswith('stderr_stream')):
            action = self._reload_stream(key, val)
        elif key.startswith('hooks'):
            val = val.split(',')
            if len(val) == 2:
                ignore_error = util.to_bool(val[1])
            else:
                ignore_error = False
            hook = val[0]
            self._reload_hook(key, hook, ignore_error)
            action = 0

        # send update event
        self.notify_event("updated", {"time": time.time()})
        return action

    @util.synchronized("watcher_do_action")
    @gen.coroutine
    def do_action(self, num):
        # trigger needed action
        if num == 0:
            yield self.manage_processes()
        elif not self.is_stopped():
            # graceful restart
            yield self._reload()

    @util.debuglog
    def options(self, *args):
        options = []
        for name in sorted(self.optnames):
            if name in self._options:
                options.append((name, self._options[name]))
            else:
                options.append((name, getattr(self, name)))
        return options

    def is_stopping(self):
        return self._status == 'stopping'

    def is_stopped(self):
        return self._status == 'stopped'

    def is_active(self):
        return self._status == 'active'
