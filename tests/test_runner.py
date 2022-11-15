from tornado.testing import gen_test
from tests.support import TestCircus, async_poll_for


def Dummy(test_file):
    with open(test_file, 'w') as f:
        f.write('..........')
    return 1


class TestRunner(TestCircus):

    @gen_test
    def test_dummy(self):
        yield self.start_arbiter('tests.test_runner.Dummy')
        res = yield async_poll_for(self.test_file, '..........')
        self.assertTrue(res)
        yield self.stop_arbiter()


