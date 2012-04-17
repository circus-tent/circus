import errno
import signal
import time

from zmq.utils.jsonapi import jsonmod as json

from circus.process import Process, DEAD_OR_ZOMBIE
from circus import logger
from circus import util
from circus.stream import get_pipe_redirector


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

    - **env**: a mapping containing the environment variables the command
      will run with. Optional.

    - **rlimits**: a mapping containing rlimit names and values that will
      be set before the command runs.

    - **stdout_stream**: a callable that will receive the stream of
      the process stdout. Defaults to None.

      When provided, *stdout_stream* is a mapping containing two keys:

      - **stream**: the callable that will receive the updates
        streaming. Defaults to :class:`circus.stream.FileStream`

      - **refresh_time**: the delay between two stream checks. Defaults
        to 0.3 seconds.

      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

    - **stderr_stream**: a callable that will receive the stream of
      the process stderr. Defaults to None.

      When provided, *stdout_stream* is a mapping containing two keys:

      - **stream**: the callable that will receive the updates
        streaming. Defaults to :class:`circus.stream.FileStream`

      - **refresh_time**: the delay between two stream checks. Defaults
        to 0.3 seconds.

      Each entry received by the callable is a mapping containing:

      - **pid** - the process pid
      - **name** - the stream name (*stderr* or *stdout*)
      - **data** - the data

    - **stream_backend** -- the backend that will be used for the streaming
      process. Can be *thread* or *gevent*. When set to *gevent* you need
      to have *gevent* and *gevent_zmq* installed. (default: thread)

    """
    def __init__(self, name, cmd, args=None, numprocesses=1, warmup_delay=0.,
                 working_dir=None, shell=False, uid=None,
                 gid=None, send_hup=False, env=None, stopped=True,
                 times=2, within=1., retry_in=7., max_retry=5,
                 graceful_timeout=30., prereload_fn=None,
                 rlimits=None, executable=None, stdout_stream=None,
                 stderr_stream=None, stream_backend='thread'):
        self.name = name
        self.res_name = name.lower().replace(" ", "_")
        self.numprocesses = int(numprocesses)
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self.args = args
        self._process_counter = 0
        self.stopped = stopped
        self.times = times
        self.within = within
        self.retry_in = retry_in
        self.max_retry = max_retry
        self.graceful_timeout = 30
        self.prereload_fn = prereload_fn
        self.executable = None
        self.stream_backend = stream_backend

        self.stdout_stream = stdout_stream
        if stdout_stream:
            self.stdout_redirector = get_pipe_redirector(stdout_stream,
                    backend=stream_backend)
        else:
            self.stdout_redirector = None

        self.stderr_stream = stderr_stream
        if stderr_stream:
            self.stderr_redirector = get_pipe_redirector(stderr_stream,
                    backend=stream_backend)
        else:
            self.stderr_redirector = None

        self.optnames = ("numprocesses", "warmup_delay", "working_dir",
                         "uid", "gid", "send_hup", "shell", "env",
                         "cmd", "times", "within", "retry_in", "args",
                         "max_retry", "graceful_timeout", "executable")

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
        self.evpub_socket = None

    @classmethod
    def load_from_config(cls, config):
        return cls(name=config['name'],
                   cmd=config['cmd'],
                   args=config.get('args'),
                   numprocesses=config.get('numprocesses', 1),
                   warmup_delay=config.get('warmup_delay', 0),
                   working_dir=config.get('working_dir'),
                   shell=config.get('shell', False),
                   uid=config.get('uid'),
                   gid=config.get('gid'),
                   send_hup=config.get('send_hup', False),
                   env=config.get('env'),
                   stopped=config.get('stopped', True),
                   times=config.get('times', 2),
                   within=config.get('within', 1),
                   retry_in=config.get('retry_in', 7),
                   max_retry=config.get('max_retry', 5),
                   graceful_timeout=config.get('graceful_timeout', 30),
                   prereload_fn=config.get('prereload_fn'),
                   rlimits=config.get('rlimits'),
                   executable=config.get('executable'),
                   stdout_stream=config.get('stdout_stream'),
                   stderr_stream=config.get('stderr_stream'),
                   stream_backend=config.get('stream_backend', 'thread'))

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

        multipart_msg = ["watcher.%s.%s" % (name, topic), json.dumps(msg)]

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
                          args=self.args, working_dir=self.working_dir,
                          shell=self.shell, uid=self.uid, gid=self.gid,
                          env=self.env, rlimits=self.rlimits,
                          executable=self.executable)

                # stream stderr/stdout if configured
                if self.stdout_redirector is not None:
                    self.stdout_redirector.add_redirection('stdout',
                                                           process,
                                                           process.stdout)

                if self.stderr_redirector is not None:
                    self.stderr_redirector.add_redirection('stderr',
                                                           process,
                                                           process.stderr)

                self.processes[self._process_counter] = process
                logger.debug('running %s process [pid %d]', self.name,
                            process.pid)
            except OSError, e:
                logger.warning('error in %r: %s', self.name, str(e))

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
        # remove redirections
        if self.stdout_redirector is not None:
            self.stdout_redirector.remove_redirection('stdout', process)

        if self.stderr_redirector is not None:
            self.stderr_redirector.remove_redirection('stderr', process)

        self.send_msg("kill", {"process_id": process.wid,
                               "time": time.time()})
        logger.debug("%s: kill process %s", self.name, process.pid)
        process.send_signal(sig)
        process.stop()

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
    def stop(self):
        """Stop.
        """
        self.stopped = True
        # stop redirectors
        if self.stdout_redirector is not None:
            self.stdout_redirector.kill()

        if self.stderr_redirector is not None:
            self.stderr_redirector.kill()

        limit = time.time() + self.graceful_timeout
        while self.processes and time.time() < limit:
            self.kill_processes(signal.SIGTERM)
            time.sleep(0.1)
            self.reap_processes()

        self.kill_processes(signal.SIGKILL)
        if self.evpub_socket is not None:
            self.send_msg("stop", {"time": time.time()})

        logger.info('%s stopped', self.name)

    @util.debuglog
    def start(self):
        """Start.
        """
        if not self.stopped:
            return

        self.stopped = False
        self.reap_processes()
        self.manage_processes()
        if self.stdout_redirector is not None:
            self.stdout_redirector.start()

        if self.stderr_redirector is not None:
            self.stderr_redirector.start()

        logger.info('%s started' % self.name)
        self.send_msg("start", {"time": time.time()})

    @util.debuglog
    def restart(self):
        """Restart.
        """
        self.send_msg("restart", {"time": time.time()})
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
            for wid, process in self.processes.items():
                logger.info("SEND HUP to %s [%s]" % (wid, process.pid))
                process.send_signal(signal.SIGHUP)
        else:
            for i in range(self.numprocesses):
                self.spawn_process()
            self.manage_processes()
        self.send_msg("reload", {"time": time.time()})
        logger.info('%s reloaded', self.name)

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
        """Set a watcher option.

        This function set the watcher options. unknown keys are ignored.
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
