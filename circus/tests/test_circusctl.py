import subprocess
import shlex
from unittest.mock import patch
from multiprocessing import Process, Queue

from tornado.testing import gen_test
from tornado.gen import coroutine, Return

from circus.circusctl import USAGE, VERSION, CircusCtl
from circus.tests.support import (TestCircus, async_poll_for, EasyTestSuite,
                                  skipIf, DEBUG, PYTHON, SLEEP)
from circus.util import (tornado_sleep, DEFAULT_ENDPOINT_DEALER, to_str,
                         to_bytes)


def run_ctl(args, queue=None, stdin='', endpoint=DEFAULT_ENDPOINT_DEALER):
    cmd = '%s -m circus.circusctl' % PYTHON
    if '--endpoint' not in args:
        args = '--endpoint %s ' % endpoint + args

    proc = subprocess.Popen(cmd.split() + shlex.split(args),
                            stdin=subprocess.PIPE if stdin else None,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate(to_bytes(stdin) if stdin else None)
    stdout = to_str(stdout)
    stderr = to_str(stderr)
    if queue:
        queue.put(stderr)
        queue.put(stdout)
        queue.put(proc.returncode)
    try:
        import gevent
        if hasattr(gevent, 'shutdown'):
            gevent.shutdown()
    except ImportError:
        pass
    return stdout, stderr


@coroutine
def async_run_ctl(args, stdin='', endpoint=DEFAULT_ENDPOINT_DEALER):
    """
    Start a process that will start the actual circusctl process and poll its
    ouput, via a queue, without blocking the I/O loop. We do this to avoid
    blocking the main thread while waiting for circusctl output, so that the
    arbiter will be able to respond to requests coming from circusctl.
    """
    queue = Queue()
    circusctl_process = Process(target=run_ctl,
                                args=(args, queue, stdin,
                                      endpoint))
    circusctl_process.start()
    while queue.empty():
        yield tornado_sleep(.1)

    stderr = queue.get()
    stdout = queue.get()
    retcode = queue.get()

    raise Return((retcode, stdout, stderr))


class CommandlineTest(TestCircus):

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_help_switch_no_command(self):
        retcode, stdout, stderr = yield async_run_ctl('--help')
        if stderr:
            self.assertIn('UserWarning', stderr)
        output = stdout.splitlines()
        self.assertEqual(retcode, 0)
        self.assertEqual(output[0], 'usage: ' + USAGE)
        self.assertEqual(output[2], 'Controls a Circus daemon')
        self.assertEqual(output[4], 'Commands:')

    @gen_test
    def test_help_invalid_command(self):
        retcode, stdout, stderr = yield async_run_ctl('foo')
        self.assertEqual(stdout, '')
        err = stderr.splitlines()
        while err and 'import' in err[0]:
            del err[0]
        self.assertEqual(retcode, 2)
        self.assertEqual(err[0], 'usage: ' + USAGE)
        self.assertEqual(err[1],
                         'circusctl.py: error: unrecognized arguments: foo')

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_help_for_add_command(self):
        retcode, stdout, stderr = yield async_run_ctl('--help add')
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(retcode, 0)
        self.assertEqual(stdout.splitlines()[0], 'Add a watcher')

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_add(self):
        yield self.start_arbiter()
        yield async_poll_for(self.test_file, 'START')
        ep = self.arbiter.endpoint

        retcode, stdout, stderr = yield async_run_ctl(
            'add test2 "%s"' % SLEEP % 1, endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(retcode, 0)
        self.assertEqual(stdout.strip(), 'ok')

        retcode, stdout, stderr = yield async_run_ctl(
            'status test2', endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(retcode, 0)
        self.assertEqual(stdout.strip(), 'stopped')
        yield self.stop_arbiter()

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_add_start(self):
        yield self.start_arbiter()
        yield async_poll_for(self.test_file, 'START')
        ep = self.arbiter.endpoint

        retcode, stdout, stderr = yield async_run_ctl(
            'add --start test2 "%s"' % SLEEP % 1, endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(retcode, 0)
        self.assertEqual(stdout.strip(), 'ok')
        retcode, stdout, stderr = yield async_run_ctl(
            'status test2', endpoint=ep)
        if stderr:
            self.assertIn('UserWarning', stderr)
        self.assertEqual(retcode, 0)
        self.assertEqual(stdout.strip(), 'active')
        yield self.stop_arbiter()

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_command_already_running(self):
        yield self.start_arbiter()
        yield async_poll_for(self.test_file, 'START')

        with patch.object(self.arbiter, '_exclusive_running_command', 'foo'):
            retcode, stdout, stderr = yield async_run_ctl(
                'restart', endpoint=self.arbiter.endpoint)

        self.assertEqual(retcode, 3)
        self.assertEqual(stdout.strip(), '')
        self.assertEqual(stderr.strip(),
                         'error: arbiter is already running foo command')


class CLITest(TestCircus):

    @coroutine
    def run_ctl(self, command='', endpoint=DEFAULT_ENDPOINT_DEALER):
        """Send the given command to the CLI, and ends with EOF."""
        if command:
            command += '\n'
        retcode, stdout, stderr = yield async_run_ctl(
            '', command + 'EOF\n', endpoint=endpoint)
        raise Return((retcode, stdout, stderr))

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @gen_test
    def test_launch_cli(self):
        yield self.start_arbiter()
        yield async_poll_for(self.test_file, 'START')

        retcode, stdout, stderr = yield self.run_ctl(
            endpoint=self.arbiter.endpoint)
        if stderr:
            self.assertIn('UserWarning', stderr)
        output = stdout.splitlines()
        self.assertEqual(output[0], VERSION)
        # strip off term escape characters, if any
        if not output[2].startswith(CircusCtl.prompt):
            prompt = output[2][-len(CircusCtl.prompt):]
            self.assertEqual(prompt, CircusCtl.prompt)

        yield self.stop_arbiter()

    @gen_test
    def test_cli_help(self):
        yield self.start_arbiter()
        retcode, stdout, stderr = yield self.run_ctl(
            'help', endpoint=self.arbiter.endpoint)
        self.assertEqual(stderr, '')
        prompt = stdout.splitlines()
        # first two lines are VERSION and prompt, followed by a blank line
        self.assertEqual(prompt[3], "Documented commands (type help <topic>):")
        yield self.stop_arbiter()


test_suite = EasyTestSuite(__name__)
