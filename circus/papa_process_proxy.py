__author__ = 'Scott Maxwell'

from circus.process import Process, debuglog
from circus.util import papa
import psutil
import select
import time

# TODO(papa) Make all processes for a watcher use the same redirector
# TODO(papa) Verify that sockets are set as use_papa
# TODO(papa) Save state of watchers to papa
# TODO(papa) Recover state of watchers on startup
# TODO(papa) Remove sockets on stop or restart all
# TODO(papa) Add support for OS-assigned ports


def _bools_to_papa_out(pipe, close):
    return papa.PIPE if pipe else papa.DEVNULL if close else None


class PapaProcessWorker(psutil.Process):
    # noinspection PyMissingConstructor
    def __init__(self, proxy, pid):
        self._init(pid, _ignore_nsp=True)
        self._proxy = proxy

    def wait(self, timeout=None):
        return self._proxy.wait(timeout)


class PapaProcessProxy(Process):
    def __init__(self, *args, **kwargs):
        self._papa = None
        self._papa_watcher = None
        self._papa_name = None
        super(PapaProcessProxy, self).__init__(*args, **kwargs)

    @staticmethod
    def _fix_socket_name(s):
        if s:
            while '$(circus.sockets.' in s:
                start = s.index('$(circus.sockets.')
                end = s.index(')', start)
                s = s[:start] + '$(socket.circus.' + s[start + 17:end] + '.fileno)' + s[end + 1:]
        return s

    def spawn(self):
        self.cmd = self._fix_socket_name(self.cmd)
        self.args = [self._fix_socket_name(arg) for arg in self.args]
        args = self.format_args()
        stdout = _bools_to_papa_out(self.pipe_stdout, self.close_child_stdout)
        stderr = _bools_to_papa_out(self.pipe_stderr, self.close_child_stderr)
        papa_name = 'circus.{0}.{1}'.format(self.name, self.wid)
        self._papa_name = papa_name
        self._papa = papa.Papa()
        p = self._papa.make_process(papa_name,
                                    executable=self.executable, args=args,
                                    env=self.env, working_dir=self.working_dir,
                                    uid=self.uid, gid=self.gid,
                                    rlimits=self.rlimits,
                                    stdout=stdout, stderr=stderr)
        self._worker = PapaProcessWorker(self, p['pid'])
        self._papa_watcher = self._papa.watch_processes(papa_name)

    def returncode(self):
        exit_code = self._papa_watcher.exit_code.get(self._papa_name)
        if exit_code is None and not self.redirected and self._papa_watcher.ready:
            self._papa_watcher.read()
            exit_code = self._papa_watcher.exit_code.get(self._papa_name)
        return exit_code

    @debuglog
    def poll(self):
        return self.returncode()

    def close_output_channels(self):
        self._papa_watcher.close()
        if self.is_alive():
            self._papa.remove_processes(self._papa_name)

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
