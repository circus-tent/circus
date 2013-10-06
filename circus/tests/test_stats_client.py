import time
import tempfile
import os
import sys

from circus.tests.support import TestCircus, EasyTestSuite
from circus.client import CircusClient
from circus.stream import FileStream
from circus.py3compat import get_next


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


class TestStatsClient(TestCircus):

    def setUp(self):
        super(TestStatsClient, self).setUp()
        self.files = []

    def _get_file(self):
        fd, log = tempfile.mkstemp()
        os.close(fd)
        self.files.append(log)
        return log

    def tearDown(self):
        super(TestStatsClient, self).tearDown()
        for file in self.files:
            if os.path.exists(file):
                os.remove(file)

    def test_handler(self):
        log = self._get_file()
        stream = {'stream': FileStream(log)}
        self._run_circus('circus.tests.test_stats_client.run_process',
                         stdout_stream=stream, stderr_stream=stream,
                         stats=True)

        # waiting for data to appear in the file stream
        empty = True
        while empty:
            with open(log) as f:
                empty = f.read() == ''

            time.sleep(.1)

        # checking that our system is live and running
        client = CircusClient()
        res = client.send_message('list')
        watchers = res['watchers']
        watchers.sort()
        self.assertEqual(['circusd-stats', 'test'], watchers)

        # making sure the stats process run
        res = client.send_message('status', name='test')
        self.assertEqual(res['status'], 'active')

        res = client.send_message('status', name='circusd-stats')
        self.assertEqual(res['status'], 'active')

        # playing around with the stats now: we should get some !
        from circus.stats.client import StatsClient
        client = StatsClient()
        next = get_next(client.iter_messages())

        for i in range(10):
            watcher, pid, stat = next()
            self.assertTrue(watcher in ('test', 'circusd-stats', 'circus'),
                            watcher)

test_suite = EasyTestSuite(__name__)
