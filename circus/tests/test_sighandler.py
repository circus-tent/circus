from circus.tests.support import TestCircus, poll_for


class TestSigHandler(TestCircus):

    def test_handler(self):
        test_file = self._run_circus(
            'circus.tests.support.run_process')

        # wait for the process to be started
        self.assertTrue(poll_for(test_file, 'START'))

        # stopping...
        self._stop_runners()

        # wait for the process to be stopped
        self.assertTrue(poll_for(test_file, 'QUIT'))
