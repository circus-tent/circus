from circus.tests.support import TestCircus
import time


class Process(object):

    def __init__(self, testfile):
        self.testfile = testfile
        # init signal handling
        import signal
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGCHLD, self.handle_chld)
        self.alive = True

    def _write(self, msg):
        with open(self.testfile, 'a+') as f:
            f.write(msg)

    def handle_quit(self, *args):
        if not self.alive:
            return
        self.alive = False
        self._write('QUIT')
        import sys
        sys.exit(0)

    def handle_chld(self, *args):
        self._write('CHLD')
        return

    def run(self):
        self._write('START')
        while self.alive:
            time.sleep(0.1)
        self._write('STOP')


def run_process(test_file):
    process = Process(test_file)
    process.run()
    return 1


class TestSigHandler(TestCircus):

    def test_handler(self):
        test_file = \
                self._run_circus('circus.tests.test_sighandler.run_process')
        time.sleep(.5)

        # stopping...
        self._stop_runners()

        time.sleep(.1)

        # check that the file has been filled
        with open(test_file) as f:
            content = f.read()

        self.assertEqual(content, 'STARTQUIT')
