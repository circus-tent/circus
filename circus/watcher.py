import copy
import errno
import os
import signal
import time
import sys
from random import randint

from psutil import NoSuchProcess
from zmq.utils.jsonapi import jsonmod as json

from circus.process import Process, DEAD_OR_ZOMBIE, UNEXISTING
from circus import logger
from circus import util
from circus.stream import get_pipe_redirector, get_stream
from circus.util import parse_env_dict, resolve_name


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
      - **refresh_time**: the delay between two stream checks. Defaults
        to 0.3 seconds.
      - **max_bytes**: maximum file size, after which a new output file is
        opened. defaults to 0 which means no maximum size.
      - **backup_count**: how many backups to retain when rotating files
        according to the max_bytes parameter. defaults to 0 which means
        no backups are made.

      This mapping will be used to create a stream callable of the specified
      class.
      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

    - **stderr_stream**: a mapping that defines the stream for
      the process stderr. Defaults to None.

      Optional. When provided, *stderr_stream* is a mapping containing up to
      three keys:
      - **class**: the stream class. Defaults to `circus.stream.FileStream`
      - **filename**: the filename, if using a FileStream
      - **refresh_time**: the delay between two stream checks. Defaults
        to 0.3 seconds.
      - **max_bytes**: maximum file size, after which a new output file is
        opened. defaults to 0 which means no maximum size.
      - **backup_count**: how many backups to retain when rotating files
        according to the max_bytes parameter. defaults to 0 which means
        no backups are made.

      This mapping will be used to create a stream callable of the specified
      class.

      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

    - **stream_backend** -- the backend that will be used for the streaming
      process. Can be *thread* or *gevent*. When set to *gevent* you need
      to have *gevent* and *gevent_zmq* installed. (default: thread)

    - **priority** -- integer that defines a priority for the watcher. When
      the Arbiter do some operations on all watchers, it will sort them
      with this field, from the bigger number to the smallest.
      (default: 0)

    - **singleton** -- If True, this watcher has a single process.
      (default:False)

    - **use_sockets** -- If True, the processes will inherit the file
      descriptors, thus can reuse the sockets opened by circusd.
      (default: False)

    - **copy_env** -- If True, the environment in which circus is running
      run will be reproduced for the workers. (default: False)

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
      or the callabled itself and a boolean flag indicating if an
      exception occuring in the hook should not be ignored.
      Possible values for the hook name: *before_start*, *after_start*,
      *before_stop*, *after_stop*.

    - **options** -- extra options for the worker. All options
      found in the configuration file for instance, are passed
      in this mapping -- this can be used by plugins for watcher-specific
      options.

    - **respawn** -- If set to False, the processes handled by a watcher will
      not be respawned automatically. (default: True)
    """
    def __init__(self, name, cmd, args=None, numprocesses=1, warmup_delay=0.,
                 working_dir=None, shell=False, uid=None, max_retry=5,
                 gid=None, send_hup=False, env=None, stopped=True,
                 graceful_timeout=30., prereload_fn=None,
                 rlimits=None, executable=None, stdout_stream=None,
                 stderr_stream=None, stream_backend='thread', priority=0,
                 singleton=False, use_sockets=False, copy_env=False,
                 copy_path=False, max_age=0, max_age_variance=30,
                 hooks=None, respawn=True, **options):
        self.name = name
        self.use_sockets = use_sockets
        self.res_name = name.lower().replace(" ", "_")
        self.numprocesses = int(numprocesses)
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self.args = args
        self._process_counter = 0
        self.stopped = stopped
        self.graceful_timeout = float(graceful_timeout)
        self.prereload_fn = prereload_fn
        self.executable = None
        self.stream_backend = stream_backend
        self.priority = priority
        self.stdout_stream_conf = copy.copy(stdout_stream)
        self.stderr_stream_conf = copy.copy(stderr_stream)
        self.stdout_stream = get_stream(self.stdout_stream_conf)
        self.stderr_stream = get_stream(self.stderr_stream_conf)
        self.stdout_redirector = self.stderr_redirector = None
        self.max_retry = max_retry
        self._options = options
        self.singleton = singleton
        self.copy_env = copy_env
        self.copy_path = copy_path
        self.max_age = int(max_age)
        self.max_age_variance = int(max_age_variance)
        self.ignore_hook_failure = ['before_stop', 'after_stop']
        self.hooks = self._resolve_hooks(hooks)
        self.respawn = respawn

        if singleton and self.numprocesses not in (0, 1):
            raise ValueError("Cannot have %d processes with a singleton "
                             " watcher" % self.numprocesses)

        self.optnames = (("numprocesses", "warmup_delay", "working_dir",
                          "uid", "gid", "send_hup", "shell", "env",
                          "max_retry", "cmd", "args", "graceful_timeout",
                          "executable", "use_sockets", "priority", "copy_env",
                          "singleton", "stdout_stream_conf",
                          "stderr_stream_conf", "max_age", "max_age_variance")
                         + tuple(options.keys()))

        if not working_dir:
            # working dir hasn't been set
            working_dir = util.get_working_dir()

        self.working_dir = working_dir
        self.processes = {}
        self.shell = shell
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

        self.rlimits = rlimits
        self.send_hup = send_hup
        self.sockets = self.evpub_socket = None
        self.arbiter = None

    def _create_redirectors(self):
        if self.stdout_stream:
            if (self.stdout_redirector is not None and
                    self.stdout_redirector.running):
                self.stdout_redirector.kill()
            self.stdout_redirector = get_pipe_redirector(
                self.stdout_stream, backend=self.stream_backend)
        else:
            self.stdout_redirector = None

        if self.stderr_stream:
            if (self.stderr_redirector is not None and
                    self.stderr_redirector.running):
                self.stderr_redirector.kill()

            self.stderr_redirector = get_pipe_redirector(
                self.stderr_stream, backend=self.stream_backend)
        else:
            self.stderr_redirector = None

    def _resolve_hooks(self, hooks):
        """Check the supplied hooks argument to make sure we can find
        callables"""
        if not hooks:
            return {}

        resolved_hooks = {}

        for hook_name, hook_value in hooks.items():
            callable_or_name, ignore_failure = hook_value

            if callable(callable_or_name):
                resolved_hooks[hook_name] = callable_or_name
            else:
                # will raise ImportError on failure
                resolved_hook = resolve_name(callable_or_name)
                resolved_hooks[hook_name] = resolved_hook

            if ignore_failure:
                self.ignore_hook_failure.append(hook_name)

        return resolved_hooks

    @classmethod
    def load_from_config(cls, config):
        if 'env' in config:
            config['env'] = parse_env_dict(config['env'])
        return cls(name=config.pop('name'), cmd=config.pop('cmd'), **config)

    @util.debuglog
    def initialize(self, evpub_socket, sockets, arbiter):
        self.evpub_socket = evpub_socket
        self.sockets = sockets
        self.arbiter = arbiter

    def __len__(self):
        return len(self.processes)

    def notify_event(self, topic, msg):
        """Publish a message on the event publisher channel"""

        json_msg = json.dumps(msg)
        if isinstance(json_msg, unicode):
            json_msg = json_msg.encode('utf8')

        if isinstance(self.res_name, unicode):
            name = self.res_name.encode('utf8')
        else:
            name = self.res_name

        multipart_msg = ["watcher.%s.%s" % (name, topic), json.dumps(msg)]

        if self.evpub_socket is not None and not self.evpub_socket.closed:
            self.evpub_socket.send_multipart(multipart_msg)

    @util.debuglog
    def reap_process(self, pid, status=None):
        """ensure that the process is killed (and not a zombie)"""
        process = self.processes.pop(pid)

        if not status:
            while True:
                try:
                    _, status = os.waitpid(pid, os.WNOHANG)
                except OSError as e:
                    if e.errno == errno.EAGAIN:
                        time.sleep(0.001)
                        continue
                    elif e.errno == errno.ECHILD:
                        # nothing to do here, we do not have any child
                        # process running
                        return
                    else:
                        raise

        # get return code
        if os.WIFSIGNALED(status):
            os.WTERMSIG(status)
        # process exited using exit(2) system call; return the
        # integer exit(2) system call has been called with
        elif os.WIFEXITED(status):
            os.WEXITSTATUS(status)
        else:
            # should never happen
            raise RuntimeError("Unknown process exit status")

        # if the process is dead or a zombie try to definitely stop it.
        if process.status in (DEAD_OR_ZOMBIE, UNEXISTING):
            process.stop()

        logger.debug('reaping process %s [%s]' % (pid, self.name))
        self.notify_event("reap", {"process_pid": pid, "time": time.time()})

    @util.debuglog
    def reap_processes(self):
        """Reap all the processes for this watcher.
        """
        if self.stopped:
            logger.debug('do not reap processes as the watcher is stopped')
            return

        # reap_process changes our dict, look through the copy of keys
        for pid in self.processes.keys():
            self.reap_process(pid)

    @util.debuglog
    def manage_processes(self):
        """Manage processes."""
        if self.stopped:
            return

        if self.max_age:
            for process in self.processes.itervalues():
                max_age = self.max_age + randint(0, self.max_age_variance)
                if process.age() > max_age:
                    logger.debug('%s: expired, respawning', self.name)
                    self.notify_event("expired",
                                      {"process_pid": process.pid,
                                       "time": time.time()})
                    self.kill_process(process)

        if self.respawn and len(self.processes) < self.numprocesses:
            self.spawn_processes()

        processes = self.processes.values()
        processes.sort()
        while len(processes) > self.numprocesses:
            process = processes.pop(0)
            if process.status == DEAD_OR_ZOMBIE:
                self.processes.pop(process.pid)
            else:
                self.processes.pop(process.pid)
                self.kill_process(process)

    @util.debuglog
    def reap_and_manage_processes(self):
        """Reap & manage processes."""
        if self.stopped:
            return
        self.reap_processes()
        self.manage_processes()

    @util.debuglog
    def spawn_processes(self):
        """Spawn processes.
        """
        for i in range(self.numprocesses - len(self.processes)):
            self.spawn_process()
            time.sleep(self.warmup_delay)

    def _get_sockets_fds(self):
        # XXX should be cached
        if self.sockets is None:
            return {}
        fds = {}
        for name, sock in self.sockets.items():
            fds[name] = sock.fileno()
        return fds

    def spawn_process(self):
        """Spawn process.
        """
        if self.stopped:
            return

        cmd = util.replace_gnu_args(self.cmd, sockets=self._get_sockets_fds())
        self._process_counter += 1
        nb_tries = 0
        while nb_tries < self.max_retry:
            process = None
            try:
                process = Process(self._process_counter, cmd,
                                  args=self.args, working_dir=self.working_dir,
                                  shell=self.shell, uid=self.uid, gid=self.gid,
                                  env=self.env, rlimits=self.rlimits,
                                  executable=self.executable,
                                  use_fds=self.use_sockets, watcher=self)

                # stream stderr/stdout if configured
                if self.stdout_redirector is not None:
                    self.stdout_redirector.add_redirection('stdout',
                                                           process,
                                                           process.stdout)

                if self.stderr_redirector is not None:
                    self.stderr_redirector.add_redirection('stderr',
                                                           process,
                                                           process.stderr)

                self.processes[process.pid] = process
                logger.debug('running %s process [pid %d]', self.name,
                             process.pid)
            except OSError, e:
                logger.warning('error in %r: %s', self.name, str(e))

            if process is None:
                nb_tries += 1
                continue
            else:
                self.notify_event("spawn", {"process_pid": process.pid,
                                            "time": time.time()})
                time.sleep(self.warmup_delay)
                return

        self.stop()

    def kill_process(self, process, sig=signal.SIGTERM):
        """Kill process.
        """
        # remove redirections
        if self.stdout_redirector is not None:
            self.stdout_redirector.remove_redirection('stdout', process)

        if self.stderr_redirector is not None:
            self.stderr_redirector.remove_redirection('stderr', process)

        logger.debug("%s: kill process %s", self.name, process.pid)
        try:
            # sending the same signal to all the children
            for child_pid in process.children():
                process.send_signal_child(child_pid, sig)
                self.notify_event("kill", {"process_pid": child_pid,
                                  "time": time.time()})

            # now sending the signal to the process itself
            self.send_signal(process.pid, sig)
            self.notify_event("kill", {"process_pid": process.pid,
                                       "time": time.time()})

        except NoSuchProcess:
            # already dead !
            return

        process.stop()

    @util.debuglog
    def kill_processes(self, sig):
        """Kill all the processes of this watcher.
        """

        for process in self.get_active_processes():
            try:
                self.kill_process(process, sig)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    @util.debuglog
    def send_signal(self, pid, signum):
        if pid in self.processes:
            process = self.processes[pid]
            process.send_signal(signum)
        else:
            logger.debug('process %s does not exist' % pid)

    def send_signal_processes(self, signum):
        for pid in self.processes:
            try:
                self.send_signal(pid, signum)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

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
    def send_signal_children(self, pid, signum):
        """Send signal to all children.
        """
        process = self.processes[int(pid)]
        process.send_signal_children(signum)

    @util.debuglog
    def status(self):
        if self.stopped:
            return "stopped"
        return "active"

    @util.debuglog
    def process_info(self, pid):
        process = self.processes[int(pid)]
        return process.info()

    @util.debuglog
    def info(self):
        return dict([(proc.pid, proc.info())
                     for proc in self.processes.values()])

    @util.debuglog
    def stop(self):
        """Stop.
        """
        logger.debug('stopping the %s watcher' % self.name)

        # stop redirectors
        if self.stdout_redirector is not None:
            self.stdout_redirector.kill()

        if self.stderr_redirector is not None:
            self.stderr_redirector.kill()

        limit = time.time() + self.graceful_timeout

        logger.debug('gracefully stopping processes [%s] for %ss' % (
                     self.name, self.graceful_timeout))

        # We ignore the hook result
        self.call_hook('before_stop')

        while self.get_active_processes() and time.time() < limit:
            self.kill_processes(signal.SIGTERM)
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                pass
            self.reap_processes()

        self.kill_processes(signal.SIGKILL)

        if self.evpub_socket is not None:
            self.notify_event("stop", {"time": time.time()})

        self.stopped = True

        # We ignore the hook result
        self.call_hook('after_stop')
        logger.info('%s stopped', self.name)

    def get_active_processes(self):
        """return a list of pids of active processes (not already stopped)"""
        return [p for p in self.processes.values()
                if p.status not in (DEAD_OR_ZOMBIE, UNEXISTING)]

    @property
    def pids(self):
        """Returns a list of PIDs"""
        return [process.pid for process in self.processes]

    def call_hook(self, hook_name):
        """Call a hook function"""
        kwargs = {'watcher': self, 'arbiter': self.arbiter,
                  'hook_name': hook_name}

        if hook_name in self.hooks:
            try:
                result = self.hooks[hook_name](**kwargs)
                error = None
                self.notify_event("hook_success",
                                  {"name": hook_name, "time": time.time()})
            except Exception, error:
                logger.exception('Hook %r failed' % hook_name)
                result = hook_name in self.ignore_hook_failure
                self.notify_event("hook_failure",
                                  {"name": hook_name, "time": time.time(),
                                   "error": str(error)})

            return result
        else:
            return True

    @util.debuglog
    def start(self):
        """Start.
        """
        if not self.stopped:
            return

        self.stopped = False

        if not self.call_hook('before_start'):
            logger.debug('Aborting startup')
            self.stopped = True
            return False

        self._create_redirectors()
        self.reap_processes()
        self.spawn_processes()

        if not self.call_hook('after_start'):
            logger.debug('Aborting startup')
            self.stop()
            return False

        if self.stdout_redirector is not None:
            self.stdout_redirector.start()

        if self.stderr_redirector is not None:
            self.stderr_redirector.start()

        logger.info('%s started' % self.name)
        self.notify_event("start", {"time": time.time()})
        return True

    @util.debuglog
    def restart(self):
        """Restart.
        """
        self.notify_event("restart", {"time": time.time()})
        self.stop()
        if self.start():
            logger.info('%s restarted', self.name)
        else:
            logger.info('Failed to restart %s', self.name)

    @util.debuglog
    def reload(self, graceful=True):
        """ reload
        """
        if self.prereload_fn is not None:
            self.prereload_fn(self)

        if not graceful:
            return self.restart()

        if self.send_hup:
            for process in self.processes.values():
                logger.info("SENDING HUP to %s" % process.pid)
                process.send_signal(signal.SIGHUP)
        else:
            for i in range(self.numprocesses):
                self.spawn_process()
            self.manage_processes()
        self.notify_event("reload", {"time": time.time()})
        logger.info('%s reloaded', self.name)

    @util.debuglog
    def incr(self, nb=1):
        if self.singleton and self.numprocesses == 1:
            raise ValueError('Singleton watcher has a single process')

        self.numprocesses += nb
        self.manage_processes()
        return self.numprocesses

    @util.debuglog
    def decr(self, nb=1):
        if self.numprocesses > 0:
            self.numprocesses -= nb
            self.manage_processes()
        return self.numprocesses

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
        elif key == "shell":
            self.shell = val
            action = 1
        elif key == "env":
            self.env = val
            action = 1
        elif key == "cmd":
            self.cmd = val
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

        # send update event
        self.notify_event("updated", {"time": time.time()})
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
        options = []
        for name in sorted(self.optnames):
            if name in self._options:
                options.append((name, self._options[name]))
            else:
                options.append((name, getattr(self, name)))
        return options
