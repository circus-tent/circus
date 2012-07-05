import time
import signal
import sys
import os

from circus.client import CircusClient, make_message
from circus.tests.support import TestCircus
from circus.stream import QueueStream
from circus.watcher import Watcher


def run_process(test_file):
    try:
        i = 0
        while True:
            sys.stdout.write('%d-%s\\n' % (os.getpid(), i))
            sys.stdout.flush()
            time.sleep(1)
    except:
        return 1


class TestWatcher(TestCircus):

    def setUp(self):
        super(TestWatcher, self).setUp()
        self.stream = QueueStream()
        dummy_process = 'circus.tests.test_watcher.run_process'
        self.test_file = self._run_circus(dummy_process,
                stdout_stream={'stream': self.stream})
        self.cli = CircusClient()

    def call(self, cmd, **props):
        msg = make_message(cmd, **props)
        return self.cli.call(msg)

    def tearDown(self):
        super(TestWatcher, self).tearDown()
        self.cli.stop()

    def status(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('status')

    def numprocesses(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('numprocesses')

    def test_signal(self):
        self.assertEquals(self.numprocesses('incr', name='test'), 2)

        def get_pids():
            return self.call('list', name='test').get('pids')

        pids = get_pids()
        self.assertEquals(len(pids), 2)
        to_kill = pids[0]
        self.assertEquals(self.status('signal', name='test', pid=to_kill,
                                      signum=signal.SIGKILL), 'ok')

        time.sleep(1)  # wait for the process to die

        # we still should have two processes, but not the same pids for them
        pids = get_pids()
        self.assertEquals(len(pids), 2)
        self.assertTrue(to_kill not in pids)

    def test_stats(self):
        resp = self.call("stats").get('infos')
        self.assertTrue("test" in resp)
        watchers = resp['test']

        self.assertEqual(watchers[watchers.keys()[0]]['cmdline'],
                         sys.executable.split(os.sep)[-1])

    def test_streams(self):
        time.sleep(1.)
        # let's see what we got
        self.assertTrue(self.stream.qsize() > 1)


class TestWatcherInitialization(TestCircus):

    def test_copy_env(self):
        old_environ = os.environ
        try:
            os.environ = {'COCONUTS': 'MIGRATE'}
            watcher = Watcher("foo", "foobar", copy_env=True)
            self.assertEquals(watcher.env, os.environ)

            watcher = Watcher("foo", "foobar", copy_env=True,
                              env={"AWESOMENESS": "YES"})
            self.assertEquals(watcher.env,
                              {'COCONUTS': 'MIGRATE', 'AWESOMENESS': 'YES'})
        finally:
            os.environ = old_environ
