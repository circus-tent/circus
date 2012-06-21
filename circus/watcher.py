import errno
import os
import signal
import time
import re

from psutil import STATUS_ZOMBIE, STATUS_DEAD, NoSuchProcess
from zmq.utils.jsonapi import jsonmod as json

from circus.process import Process, DEAD_OR_ZOMBIE
from circus import logger
from circus import util
from circus.stream import get_pipe_redirector, get_stream


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

      Optional. When provided, *stdout_stream* is a mapping containing up to three keys:
      - **class**: the stream class. Defaults to `circus.stream.FileStream`
      - **filename**: the filename, if using a FileStream
      - **refresh_time**: the delay between two stream checks. Defaults
        to 0.3 seconds.
      
      This mapping will be used to create a stream callable of the specified class.
      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

    - **stderr_stream**: a mapping that defines the stream for
      the process stderr. Defaults to None.

      Optional. When provided, *stderr_stream* is a mapping containing up to three keys:
      - **class**: the stream class. Defaults to `circus.stream.FileStream`
      - **filename**: the filename, if using a FileStream
      - **refresh_time**: the delay between two stream checks. Defaults
        to 0.3 seconds.

      This mapping will be used to create a stream callable of the specified class.
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

    = **use_sockets** -- XXX

    - **options** -- extra options for the worker. All options
      found in the configuration file for instance, are passed
      in this mapping -- this can be used by plugins for watcher-specific
      options.
    """
    def __init__(self, name, cmd, args=None, numprocesses=1, warmup_delay=0.,
                 working_dir=None, shell=False, uid=None, max_retry=5,
                 gid=None, send_hup=False, env=None, stopped=True,
                 graceful_timeout=30., prereload_fn=None,
                 rlimits=None, executable=None, stdout_stream=None,
                 stderr_stream=None, stream_backend='thread', priority=0,
                 singleton=False, use_sockets=False, **options):
        self.name = name
        self.use_sockets = use_sockets
        self.res_name = name.lower().replace(" ", "_")
        self.numprocesses = int(numprocesses)
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self.args = args
        self._process_counter = 0
        self.stopped = stopped
        self.graceful_timeout = graceful_timeout
        self.prereload_fn = prereload_fn
        self.executable = None
        self.stream_backend = stream_backend
        self.priority = priority
        self.stdout_stream = get_stream(stdout_stream)
        self.stderr_stream = get_stream(stderr_stream)
        self.stdout_redirector = self.stderr_redirector = None
        self.max_retry = max_retry
        self._options = options
        self.singleton = singleton
        if singleton and self.numprocesses not in (0, 1):
            raise ValueError("Cannot have %d processes with a singleton "
                             " watcher" % self.numprocesses)

        self.optnames = ("numprocesses", "warmup_delay", "working_dir",
                         "uid", "gid", "send_hup", "shell", "env", "max_retry",
                         "cmd", "args", "graceful_timeout", "executable",
                         "use_sockets", "priority",
                         "singleton") + tuple(options.keys())

        if not working_dir:
            # working dir hasn't been set
            working_dir = util.get_working_dir()

        self.working_dir = working_dir
        self.processes = {}
        self.shell = shell
        self.uid = uid
        self.gid = gid
        self.env = env
        self.rlimits = rlimits
        self.send_hup = send_hup
        self.sockets = self.evpub_socket = None

    def _create_redirectors(self):
        if self.stdout_stream:
            if (self.stdout_redirector is not None and
                self.stdout_redirector.running):
                self.stdout_redirector.kill()

            self.stdout_redirector = get_pipe_redirector(self.stdout_stream,
                    backend=self.stream_backend)
        else:
            self.stdout_redirector = None

        if self.stderr_stream:
            if (self.stderr_redirector is not None and
                self.stderr_redirector.running):
                self.stderr_redirector.kill()

            self.stderr_redirector = get_pipe_redirector(self.stderr_stream,
                    backend=self.stream_backend)
        else:
            self.stderr_redirector = None

    @classmethod
    def load_from_config(cls, config):
        return cls(name=config.pop('name'), cmd=config.pop('cmd'), **config)

    @util.debuglog
    def initialize(self, evpub_socket, sockets):
        self.evpub_socket = evpub_socket
        self.sockets = sockets

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

        if not self.evpub_socket.closed:
            self.evpub_socket.send_multipart(multipart_msg)

    @util.debuglog
    def reap_process(self, pid, status):
        """ensure that the process is killed (and not a zombie)"""
        process = self.processes.pop(pid)

        # get return code
        if os.WIFSIGNALED(status):
            retcode = os.WTERMSIG(status)
        # process exited using exit(2) system call; return the
        # integer exit(2) system call has been called with
        elif os.WIFEXITED(status):
            retcode = os.WEXITSTATUS(status)
        else:
            # should never happen
            raise RuntimeError("Unknown process exit status")

        # if the process is dead or a zombie try to definitely stop it.
        if retcode in (STATUS_ZOMBIE, STATUS_DEAD):
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

        while True:
            try:
                # wait for completion of all the childs of circus, if it
                # pertains to this watcher. Call reap on it.
                pid, status = os.waitpid(-1, os.WNOHANG)
                if not pid:
                    return

                if pid in self.processes:
                    self.reap_process(pid, status)

                if self.stopped:
                    logger.debug('watcher have been stopped, exit the loop')
                    return
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    time.sleep(0.001)
                    continue
                elif e.errno == errno.ECHILD:
                    return
                else:
                    raise

    @util.debuglog
    def manage_processes(self):
        """ manage processes
        """
        if self.stopped:
            return

        if len(self.processes) < self.numprocesses:
            self.spawn_processes()

        processes = self.processes.values()
        processes.sort()
        while len(processes) > self.numprocesses:
            process = processes.pop(0)
            if process.status == STATUS_DEAD:
                self.processes.pop(process.pid)
            else:
                self.processes.pop(process.pid)
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
        for i in range(self.numprocesses - len(self.processes)):
            self.spawn_process()
            time.sleep(self.warmup_delay)

    def spawn_process(self):
        """Spawn process.
        """
        if self.stopped:
            return

        def _repl(matchobj):
            name = matchobj.group(1)
            if name in self.sockets:
                return str(self.sockets[name].fileno())
            return '${socket:%s}' % name

        cmd = re.sub('\$\{socket\:(\w+)\}', _repl, self.cmd)
        self._process_counter += 1
        nb_tries = 0
        while nb_tries < self.max_retry:
            process = None
            try:
                process = Process(self._process_counter, cmd,
                          args=self.args, working_dir=self.working_dir,
                          shell=self.shell, uid=self.uid, gid=self.gid,
                          env=self.env, rlimits=self.rlimits,
                          executable=self.executable, use_fds=self.use_sockets,
                          watcher=self)

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

        try:
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

        for process in self.processes.values():
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
        return dict([(proc.pid, proc.info())\
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

        while self.get_active_pids() and time.time() < limit:
            self.kill_processes(signal.SIGTERM)
            time.sleep(0.1)
            self.reap_processes()

        self.kill_processes(signal.SIGKILL)

        if self.evpub_socket is not None:
            self.notify_event("stop", {"time": time.time()})

        self.stopped = True

        logger.info('%s stopped', self.name)

    def get_active_pids(self):
        """return a list of pids of active processes (not already stopped)"""
        return [p.pid for p in self.processes.values()
                if p.status != DEAD_OR_ZOMBIE]

    @property
    def pids(self):
        """Returns a list of PIDs"""
        return [process.pid for process in self.processes]

    @util.debuglog
    def start(self):
        """Start.
        """
        if not self.stopped:
            return

        self.stopped = False
        self._create_redirectors()
        self.reap_processes()
        self.manage_processes()

        if self.stdout_redirector is not None:
            self.stdout_redirector.start()

        if self.stderr_redirector is not None:
            self.stderr_redirector.start()

        logger.info('%s started' % self.name)
        self.notify_event("start", {"time": time.time()})

    @util.debuglog
    def restart(self):
        """Restart.
        """
        self.notify_event("restart", {"time": time.time()})
        self.stop()
        self.start()
        logger.info('%s restarted', self.name)

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
    def incr(self):
        if self.singleton and self.numprocesses == 1:
            raise ValueError('Singleton watcher has a single process')

        self.numprocesses += 1
        self.manage_processes()
        return self.numprocesses

    @util.debuglog
    def decr(self):
        if self.numprocesses > 0:
            self.numprocesses -= 1
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
