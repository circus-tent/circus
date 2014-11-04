__author__ = 'Scott Maxwell'

from circus.process import Process, debuglog
from circus.util import papa
import psutil


def _bools_to_papa_out(pipe, close):
    return papa.PIPE if pipe else papa.DEVNULL if close else None


class PapaProcessProxy(Process):
    def __init__(self, *args, **kwargs):
        super(PapaProcessProxy, self).__init__(*args, **kwargs)
        self._worker = None
        self._papa_watcher = None
        self._papa = None
        self._papa_name = 'circus.{0}.{1}'.format(self.name, self.wid)

    def spawn(self):
        stdout = _bools_to_papa_out(self.pipe_stdout, self.close_child_stdout)
        stderr = _bools_to_papa_out(self.pipe_stderr, self.close_child_stderr)
        self._papa = papa.Papa()
        p = self._papa.make_process(self._papa_name,
                                   executable=self.executable, args=self.args,
                                   env=self.env, working_dir=self.working_dir,
                                   uid=self.uid, gid=self.gid,
                                   rlimits=self.rlimits,
                                   stdout=stdout, stderr=stderr)
        self._worker = psutil.Process(p['pid'])
        self._papa_watcher = self._papa.watch(self._papa_name)

    def returncode(self):
        return 0  # self._worker.returncode

    @debuglog
    def poll(self):
        return None  # self._worker.poll()

    def close_output_channels(self):
        pass

    def wait(self, timeout=None):
        """
        Wait for the process to terminate, in the fashion
        of waitpid.

        Accepts a timeout in seconds.
        """
        pass  # self._worker.wait(timeout)

    @property
    def watcher(self):
        """Return the output watcher"""
        return self._papa_watcher
