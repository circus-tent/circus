__author__ = 'Scott Maxwell'

from circus.process import Process, debuglog
from circus.util import papa
import psutil


def _bools_to_papa_out(pipe, close):
    return papa.PIPE if pipe else papa.DEVNULL if close else None


class PapaProcessProxy(Process):
    def __init__(self, *args, **kwargs):
        super(PapaProcessProxy, self).__init__(*args, **kwargs)
        self.papa = papa.Papa()
        self.papa_name = 'circus.{0}.{1}'.format(self.name, self.wid)
        self._papa_watcher = None

    def spawn(self):
        stdout = _bools_to_papa_out(self.pipe_stdout, self.close_child_stdout)
        stderr = _bools_to_papa_out(self.pipe_stderr, self.close_child_stderr)
        p = self.papa.make_process(self.papa_name,
                                   executable=self.executable, args=self.args,
                                   env=self.env, working_dir=self.working_dir,
                                   uid=self.uid, gid=self.gid,
                                   rlimits=self.rlimits,
                                   stdout=stdout, stderr=stderr)
        self._worker = psutil.Process(p['pid'])
        self._papa_watcher = p.watch(self.papa_name)

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
    def stdout(self):
        """Return the *stdout* stream"""
        return None

    @property
    def stderr(self):
        """Return the *stdout* stream"""
        return None
