import time
import sys
import os
import tempfile

from circus.client import CircusClient, make_message
from circus.tests.support import TestCircus
from circus.stream import FileStream


def run_process(*args, **kw):
    try:
        i = 0
        while True:
            sys.stdout.write('%.2f-stdout-%d-%s\n' % (time.time(),
                                                      os.getpid(), i))
            sys.stdout.flush()
            sys.stderr.write('%.2f-stderr-%d-%s\n' % (time.time(),
                                                      os.getpid(), i))
            sys.stderr.flush()
            time.sleep(.25)
    except:
        return 1


class TestWatcher(TestCircus):

    def setUp(self):
        super(TestWatcher, self).setUp()
        dummy_process = 'circus.tests.test_stream.run_process'
        fd, log = tempfile.mkstemp()
        self.log = log
        os.close(fd)
        stream = {'stream': FileStream(log)}
        self.test_file = self._run_circus(dummy_process,
                stdout_stream=stream, stderr_stream=stream, debug=True)
        self.cli = CircusClient()

    def call(self, cmd, **props):
        msg = make_message(cmd, **props)
        return self.cli.call(msg)

    def tearDown(self):
        super(TestWatcher, self).tearDown()
        self.cli.stop()
        os.remove(self.log)

    def test_stream(self):
        time.sleep(2.)
        self.call("stats").get('infos')
        # let's see what we got in the file
        with open(self.log) as f:
            data = f.read()

        self.assertTrue('stderr' in data)
        self.assertTrue('stdout' in data)

        # restarting
        self.call('restart')
        time.sleep(1.)

        # should be running
        with open(self.log) as f:
            data = f.readlines()

        # last log should be less than one second old
        last = data[-1]
        delta = abs(time.time() - float(last.split('-')[0]))
        self.assertTrue(delta < 1., delta)
