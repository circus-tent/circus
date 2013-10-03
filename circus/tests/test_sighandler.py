from tornado.testing import gen_test

from circus.tests.support import TestCircus, poll_for


class TestSigHandler(TestCircus):

    @gen_test
    def test_handler(self):
        yield self.start_arbiter()

        # wait for the process to be started
        self.assertTrue(poll_for(self.test_file, 'START'))

        # stopping...
        yield self.arbiter.stop()

        # wait for the process to be stopped
        self.assertTrue(poll_for(self.test_file, 'QUIT'))
