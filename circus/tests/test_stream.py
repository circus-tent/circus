import time
import sys
import os
import tempfile

from circus.client import make_message
from circus.tests.support import TestCircus, poll_for, truncate_file
from circus.stream import FileStream


def run_process(*args, **kw):
    try:
        # print once, then wait
        sys.stdout.write('stdout')
        sys.stdout.flush()
        sys.stderr.write('stderr')
        sys.stderr.flush()
        while True:
            time.sleep(.25)
    except:
        return 1


class TestWatcher(TestCircus):

    def setUp(self):
        super(TestWatcher, self).setUp()
        dummy_process = 'circus.tests.test_stream.run_process'
        fd, self.stdout = tempfile.mkstemp()
        os.close(fd)
        fd, self.stderr = tempfile.mkstemp()
        os.close(fd)
        self.test_file = self._run_circus(
            dummy_process,
            stdout_stream={'stream': FileStream(self.stdout)},
            stderr_stream={'stream': FileStream(self.stderr)},
            debug=True)

    def call(self, cmd, **props):
        msg = make_message(cmd, **props)
        return self.cli.call(msg)

    def tearDown(self):
        super(TestWatcher, self).tearDown()
        os.remove(self.stdout)
        os.remove(self.stderr)

    def test_stream(self):
        # wait for the process to be started
        self.assertTrue(poll_for(self.stdout, 'stdout'))
        self.assertTrue(poll_for(self.stderr, 'stderr'))

        # clean slate
        truncate_file(self.stdout)
        truncate_file(self.stderr)
        # restart and make sure streams are still working
        self.call('restart')

        # wait for the process to be restarted
        self.assertTrue(poll_for(self.stdout, 'stdout'))
        self.assertTrue(poll_for(self.stderr, 'stderr'))
