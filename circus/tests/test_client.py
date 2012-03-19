import time

from circus.tests.support import TestCircus
from circus.client import CircusClient, make_message


def run_fly(test_file):
    try:
        while True:
            time.sleep(1)
    except:
        return 1


class TestClient(TestCircus):

    def test_handler(self):
        self._run_circus('circus.tests.test_client.run_fly')
        time.sleep(.5)

        # playing around with the show
        client = CircusClient()

        def call(cmd, **props):
            msg = make_message(cmd, **props)
            return client.call(msg)

        def status(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('status')

        def numflies(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('numflies')

        def numshows(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('numshows')

        def set(name, **opts):
            return status("set", name=name, options=opts)



        self.assertEquals(set("test", numflies=10), 'ok')
        self.assertEquals(numflies("numflies"), 10)
        self.assertEquals(set("test", numflies=1), 'ok')
        self.assertEquals(numflies("numflies"), 1)
        self.assertEquals(numshows("numshows"), 1)

        self.assertEquals(call("list").get('shows'), ['test'])
        self.assertEquals(call("list", name="test").get('flies'), [10])
        self.assertEquals(numflies("incr", name="test"), 2)
        self.assertEquals(numflies("numflies"), 2)
        self.assertEquals(numflies("decr", name="test"), 1)
        self.assertEquals(numflies("numflies"), 1)
        self.assertEquals(set("test", env={"test": 1, "test":2}), 'error')
        self.assertEquals(set("test", env={"test": '1', "test":'2'}),
                'ok')
        resp = call('get', name='test', keys=['env'])
        options = resp.get('options', {})

        self.assertEquals(options.get('env'), {'test': '1', 'test': '2'})

        client.stop()
