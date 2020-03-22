from circus.process import Process, debuglog
from circus.util import papa
from circus import logger
import psutil
import select
import time

__author__ = 'Scott Maxwell'


def _bools_to_papa_out(pipe, close):
    return papa.PIPE if pipe else papa.DEVNULL if close else None


class PapaProcessWorker(psutil.Process):
    # noinspection PyMissingConstructor
    def __init__(self, proxy, pid):
        try:
            self._init(pid, _ignore_nsp=True)
        except AttributeError:
            raise NotImplementedError(
                'PapaProcessWorker requires psutil 2.0.0 or higher. '
                'You probably have 1.x installed.')
        self._proxy = proxy

    def wait(self, timeout=None):
        return self._proxy.wait(timeout)


class PapaProcessProxy(Process):
    def __init__(self, *args, **kwargs):
        self._papa = None
        self._papa_watcher = None
        self._papa_name = None
        super(PapaProcessProxy, self).__init__(*args, **kwargs)

    def _fix_socket_name(self, s, socket_names):
        if s:
            s_lower = s.lower()
            while '$(circus.sockets.' in s_lower:
                start = s_lower.index('$(circus.sockets.')
                end = s_lower.index(')', start)
                socket_name = s_lower[start + 17:end]
                if socket_name not in socket_names:
                    logger.warning('Process "{0}" refers to socket "{1}" but '
                                   'they do not have the same "use_papa" state'
                                   .format(self.name, socket_name))
                s = ''.join((s[:start], '$(socket.circus.', socket_name,
                             '.fileno)', s[end + 1:]))
                s_lower = s.lower()
        return s

    def spawn(self):
        # noinspection PyUnusedLocal
        socket_names = set(socket_name.lower()
                           for socket_name in self.watcher._get_sockets_fds())
        self.cmd = self._fix_socket_name(self.cmd, socket_names)
        if isinstance(self.args, str):
            self.args = self._fix_socket_name(self.args, socket_names)
        else:
            self.args = [self._fix_socket_name(arg, socket_names)
                         for arg in self.args]
        args = self.format_args()
        stdout = _bools_to_papa_out(self.pipe_stdout, self.close_child_stdout)
        stderr = _bools_to_papa_out(self.pipe_stderr, self.close_child_stderr)
        papa_name = 'circus.{0}.{1}'.format(self.name, self.wid).lower()
        self._papa_name = papa_name
        self._papa = papa.Papa()
        if stderr is None and stdout is None:
            p = self._papa.list_processes(papa_name)
            if p:
                p = p[papa_name]
                if not p['running']:
                    self._papa.remove_processes(papa_name)

        try:
            p = self._papa.make_process(papa_name,
                                        executable=self.executable, args=args,
                                        env=self.env,
                                        working_dir=self.working_dir,
                                        uid=self.uid, gid=self.gid,
                                        rlimits=self.rlimits,
                                        stdout=stdout, stderr=stderr)
        except papa.Error:
            p = self._papa.list_processes(papa_name)
            if p:
                p = p[papa_name]
                logger.warning('Process "%s" wid "%d" already exists in papa. '
                               'Using the existing process.',
                               self.name, self.wid)
            else:
                raise
        self._worker = PapaProcessWorker(self, p['pid'])
        self._papa_watcher = self._papa.watch_processes(papa_name)
        self.started = p['started']

    def returncode(self):
        exit_code = self._papa_watcher.exit_code.get(self._papa_name)
        if exit_code is None and not self.redirected and\
                self._papa_watcher.ready:
            self._papa_watcher.read()
            exit_code = self._papa_watcher.exit_code.get(self._papa_name)
        return exit_code

    @debuglog
    def poll(self):
        return self.returncode()

    def close_output_channels(self):
        self._papa_watcher.close()
        if self.is_alive():
            try:
                self._papa.remove_processes(self._papa_name)
            except papa.Error:
                pass

    def wait(self, timeout=None):
        until = time.time() + timeout if timeout else None
        while self.is_alive():
            if until:
                now = time.time()
                if now >= until:
                    raise TimeoutError()
                timeout = until - now
            select.select([self._papa_watcher], [], [], timeout)
        return self.returncode()

    @property
    def output(self):
        """Return the output watcher"""
        return self._papa_watcher
