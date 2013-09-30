import time

from circus.tests.support import TestCircus, poll_for
from circus.client import make_message, CallError
from circus.stream import QueueStream


class TestClient(TestCircus):
    def setUp(self):
        super(TestClient, self).setUp()
        dummy_process = 'circus.tests.support.run_process'
        self.test_file = self._run_circus(dummy_process)
        poll_for(self.test_file, 'START')

    def status(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('status')

    def numprocesses(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('numprocesses')

    def numwatchers(self, cmd, **props):
        resp = self.call(cmd, **props)
        return resp.get('numwatchers')

    def set(self, name, **opts):
        return self.status("set", name=name, waiting=True, options=opts)

    def test_client(self):
        # playing around with the watcher
        msg = make_message("numwatchers")
        resp = self.cli.call(msg)
        self.assertEqual(resp.get("numwatchers"), 1)
        self.assertEquals(self.numprocesses("numprocesses"), 1)

        self.assertEquals(self.set("test", numprocesses=2), 'ok')
        self.assertEquals(self.numprocesses("numprocesses"), 2)

        self.assertEquals(self.set("test", numprocesses=1), 'ok')
        self.assertEquals(self.numprocesses("numprocesses"), 1)
        self.assertEquals(self.numwatchers("numwatchers"), 1)

        self.assertEquals(self.call("list").get('watchers'), ['test'])
        self.assertEquals(self.numprocesses("incr", name="test"), 2)
        self.assertEquals(self.numprocesses("numprocesses"), 2)
        self.assertEquals(self.numprocesses("incr", name="test", nb=2), 4)
        self.assertEquals(self.numprocesses("decr", name="test", nb=3), 1)
        self.assertEquals(self.numprocesses("numprocesses"), 1)
        self.assertEquals(self.set("test", env={"test": 1, "test": 2}),
                          'error')
        self.assertEquals(self.set("test", env={"test": '1', "test": '2'}),
                          'ok')
        resp = self.call('get', name='test', keys=['env'])
        options = resp.get('options', {})
        self.assertEquals(options.get('env'), {'test': '1', 'test': '2'})

        resp = self.call('stats', name='test')
        self.assertEqual(resp['status'], 'ok')

        resp = self.call('globaloptions', name='test')
        self.assertEqual(resp['options']['pubsub_endpoint'],
                         'tcp://127.0.0.1:5556')


def long_hook(*args, **kw):
    time.sleep(5)


class TestWithHook(TestCircus):

    def setUp(self):
        super(TestWithHook, self).setUp()
        self.old = self.cli.timeout

    def tearDown(self):
        super(TestWithHook, self).tearDown()
        self.cli.timeout = self.old

    def run_with_hooks(self, hooks):
        self.stream = QueueStream()
        self.errstream = QueueStream()
        dummy_process = 'circus.tests.support.run_process'
        return self._create_circus(dummy_process,
                                   stdout_stream={'stream': self.stream},
                                   stderr_stream={'stream': self.errstream},
                                   hooks=hooks)

    def test_message_id(self):
        hooks = {'before_stop': ('circus.tests.test_client.long_hook', False)}
        try:
            testfile, arbiter = self.run_with_hooks(hooks)
            msg = make_message("numwatchers")
            resp = self.cli.call(msg)
            self.assertEqual(resp.get("numwatchers"), 1)

            # this should timeout
            self.assertRaises(CallError, self.cli.call, make_message("stop"))

            # and we should get back on our feet
            del arbiter.watchers[0].hooks['before_stop']

            while arbiter.watchers[0].status() != 'stopped':
                time.sleep(.1)

            resp = self.cli.call(make_message("numwatchers"))
            self.assertEqual(resp.get("numwatchers"), 1)
        finally:
            arbiter.stop()
