from circus.tests.support import TestCircus, poll_for


def Dummy(test_file):
    with open(test_file, 'w') as f:
        f.write('..........')
    return 1


class TestRunner(TestCircus):

    def test_dummy(self):
        test_file = self._run_circus('circus.tests.test_runner.Dummy')
        self.assertTrue(poll_for(test_file, '..........'))
