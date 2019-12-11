from tornado.testing import gen_test

from circus.tests.support import TestCircus, async_poll_for, EasyTestSuite


class TestSigHandler(TestCircus):

    @gen_test
    def test_handler(self):
        yield self.start_arbiter()

        # wait for the process to be started
        res = yield async_poll_for(self.test_file, 'START')
        self.assertTrue(res)

        # stopping...
        yield self.arbiter.stop()

        # wait for the process to be stopped
        res = yield async_poll_for(self.test_file, 'QUIT')
        self.assertTrue(res)


test_suite = EasyTestSuite(__name__)
