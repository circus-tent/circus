import time

from circus.tests.support import TestCircus
from circus.client import CircusClient, make_message


def run_process(test_file):
    try:
        while True:
            time.sleep(1)
    except:
        return 1


class TestClient(TestCircus):

    def test_handler(self):
        self._run_circus('circus.tests.test_client.run_process')
        time.sleep(.5)

        # playing around with the watcher
        client = CircusClient()

        def call(cmd, **props):
            msg = make_message(cmd, **props)
            return client.call(msg)

        def status(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('status')

        def numprocesses(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('numprocesses')

        def numwatchers(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('numwatchers')

        def set(name, **opts):
            return status("set", name=name, options=opts)

        self.assertEquals(set("test", numprocesses=10), 'ok')
        self.assertEquals(numprocesses("numprocesses"), 10)
        self.assertEquals(set("test", numprocesses=1), 'ok')
        self.assertEquals(numprocesses("numprocesses"), 1)
        self.assertEquals(numwatchers("numwatchers"), 1)

        self.assertEquals(call("list").get('watchers'), ['test'])
        self.assertEquals(call("list", name="test").get('processes'), [10])
        self.assertEquals(numprocesses("incr", name="test"), 2)
        self.assertEquals(numprocesses("numprocesses"), 2)
        self.assertEquals(numprocesses("decr", name="test"), 1)
        self.assertEquals(numprocesses("numprocesses"), 1)
        self.assertEquals(set("test", env={"test": 1, "test": 2}), 'error')
        self.assertEquals(set("test", env={"test": '1', "test": '2'}),
                'ok')
        resp = call('get', name='test', keys=['env'])
        options = resp.get('options', {})

        self.assertEquals(options.get('env'), {'test': '1', 'test': '2'})

        client.stop()
