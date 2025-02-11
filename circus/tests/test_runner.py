from tornado.testing import gen_test
from circus.tests.support import TestCircus, async_poll_for, EasyTestSuite


def Dummy(test_file):
    with open(test_file, 'w') as f:
        f.write('..........')
    return 1


class TestRunner(TestCircus):

    @gen_test
    def test_dummy(self):
        yield self.start_arbiter('circus.tests.test_runner.Dummy')
        res = yield async_poll_for(self.test_file, '..........')
        self.assertTrue(res)
        yield self.stop_arbiter()


test_suite = EasyTestSuite(__name__)
