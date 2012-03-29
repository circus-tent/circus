import time
from circus.tests.support import TestCircus


def Dummy(test_file):
    with open(test_file, 'w') as f:
        f.write('..........')
    return 1


class TestRunner(TestCircus):

    def test_dummy(self):
        test_file = self._run_circus('circus.tests.test_runner.Dummy')
        time.sleep(1.)

        # check that the file has been filled
        with open(test_file) as f:
            content = f.read()

        self.assertTrue('.' in content)
