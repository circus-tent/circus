import time

from tornado.testing import gen_test
from tornado.gen import coroutine, Return

from circus.tests.support import TestCircus, EasyTestSuite
from circus.client import make_message, CallError
from circus.stream import QueueStream


class TestClient(TestCircus):

    @coroutine
    def status(self, cmd, **props):
        resp = yield self.call(cmd, **props)
        raise Return(resp.get('status'))

    @coroutine
    def numprocesses(self, cmd, **props):
        resp = yield self.call(cmd, waiting=True, **props)
        raise Return(resp.get('numprocesses'))

    @coroutine
    def numwatchers(self, cmd, **props):
        resp = yield self.call(cmd, **props)
        raise Return(resp.get('numwatchers'))

    @coroutine
    def set(self, name, **opts):
        resp = yield self.status("set", name=name, waiting=True, options=opts)
        raise Return(resp)

    @gen_test
    def test_client(self):
        # playing around with the watcher
        yield self.start_arbiter()
        msg = make_message("numwatchers")
        resp = yield self.cli.call(msg)
        self.assertEqual(resp.get("numwatchers"), 1)
        self.assertEqual((yield self.numprocesses("numprocesses")), 1)

        self.assertEqual((yield self.set("test", numprocesses=2)), 'ok')
        self.assertEqual((yield self.numprocesses("numprocesses")), 2)

        self.assertEqual((yield self.set("test", numprocesses=1)), 'ok')
        self.assertEqual((yield self.numprocesses("numprocesses")), 1)
        self.assertEqual((yield self.numwatchers("numwatchers")), 1)

        self.assertEqual((yield self.call("list")).get('watchers'), ['test'])
        self.assertEqual((yield self.numprocesses("incr", name="test")), 2)
        self.assertEqual((yield self.numprocesses("numprocesses")), 2)
        self.assertEqual((yield self.numprocesses("incr", name="test", nb=2)),
                         4)
        self.assertEqual((yield self.numprocesses("decr", name="test", nb=3)),
                         1)
        self.assertEqual((yield self.numprocesses("numprocesses")), 1)
        self.assertEqual((yield self.set("test", env={"test": 2})),
                         'error')
        self.assertEqual((yield self.set("test", env={"test": '2'})),
                         'ok')
        resp = yield self.call('get', name='test', keys=['env'])
        options = resp.get('options', {})
        self.assertEqual(options.get('env'), {'test': '2'})

        resp = yield self.call('stats', name='test')
        self.assertEqual(resp['status'], 'ok')

        resp = yield self.call('globaloptions', name='test')
        self.assertEqual(resp['options']['pubsub_endpoint'],
                         self.arbiter.pubsub_endpoint)
        yield self.stop_arbiter()


def long_hook(*args, **kw):
    time.sleep(5)


class TestWithHook(TestCircus):

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
        testfile, arbiter = self.run_with_hooks(hooks)
        try:
            msg = make_message("numwatchers")
            resp = yield self.cli.call(msg)
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

test_suite = EasyTestSuite(__name__)
