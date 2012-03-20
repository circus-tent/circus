import unittest
from tempfile import mkstemp
import os
import threading
import time
import sys
from circus import get_arbiter


def resolve_name(name):
    ret = None
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]
    last_exc = None

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError, exc:
            last_exc = exc
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            if last_exc is not None:
                raise last_exc
            raise ImportError(name)

    if ret is None:
        if last_exc is not None:
            raise last_exc
        raise ImportError(name)

    return ret


class Runner(threading.Thread):
    def __init__(self, arbiter, test_file):
        threading.Thread.__init__(self)
        self.arbiter = arbiter
        self.test_file = test_file

    def run(self):
        self.arbiter.start()

    def stop(self):
        time.sleep(0.25)
        self.arbiter.stop()
        self.join()


class TestCircus(unittest.TestCase):

    def setUp(self):
        self.runners = []
        self.files = []

    def tearDown(self):
        self._stop_runners()
        for file in self.files:
            if os.path.exists(file):
                os.remove(file)

    def _run_circus(self, callable):
        resolve_name(callable)   # used to check the callable
        fd, testfile = mkstemp()
        os.close(fd)
        wdir = os.path.dirname(__file__)
        cmd = '%s generic.py %s %s' % (sys.executable, callable, testfile)
        arbiter = get_arbiter(cmd, working_dir=wdir, numprocesses=1,
                              name="test")
        runner = Runner(arbiter, testfile)
        runner.start()
        self.runners.append(runner)
        self.files.append(testfile)
        return testfile

    def _stop_runners(self):
        for runner in self.runners:
            runner.stop()
        self.runners = []
