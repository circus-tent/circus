import time

from circus.tests.support import TestCircus
from circus.client import CircusClient


def run_fly(test_file):
    try:
        while True:
            time.sleep(1)
    except:
        return 1


class TestSigHandler(TestCircus):

    def test_handler(self):
        test_file = self._run_circus('circus.tests.test_client.run_fly')
        time.sleep(.5)

        # playing around with the show
        client = CircusClient()
        call = client.call

        self.assertEquals(call('set test numflies 10'), 'ok')
        self.assertEquals(call("numflies"), '10')
        self.assertEquals(call('set test numflies 1'), 'ok')
        self.assertEquals(call("numflies"), '1')
        self.assertEquals(call("numshows"), '1')
        self.assertEquals(call("shows"), 'test')
        self.assertEquals(call("flies"), 'test: 10')
        self.assertEquals(call("ttin test"), '2')
        self.assertEquals(call("numflies"), '2')
        self.assertEquals(call("ttou test"), '1')
        self.assertEquals(call("numflies"), '1')
        self.assertEquals(call('set test env test=1,test2=2'), 'ok')
        self.assertEquals(call('get test env test=1,test2=2'),
                          'test=1,test2=2')
