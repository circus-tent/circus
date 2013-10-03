import subprocess
import sys
import shlex
from multiprocessing import Process, Queue

from tornado.testing import gen_test
from tornado.gen import coroutine, Return

from circus.circusctl import USAGE, VERSION, CircusCtl
from circus.tests.support import TestCircus, poll_for
from circus.util import tornado_sleep


def run_ctl(args, queue=None, stdin=''):
    cmd = '%s -m circus.circusctl' % sys.executable
    proc = subprocess.Popen(cmd.split() + shlex.split(args),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if stdin:
        proc.stdin.write(stdin)

    stderr = proc.stderr.read()
    stdout = proc.stdout.read()
    if queue:
        queue.put(stderr)
        queue.put(stdout)
    proc.wait()
    try:
        import gevent
        gevent.shutdown()
    except ImportError:
        pass
    return stdout, stderr


@coroutine
def async_run_ctl(args, stdin=''):
    """
    Start a process that will start the actual circusctl process and poll its
    ouput, via a queue, without blocking the I/O loop. We do this to avoid
    blocking the main thread while waiting for circusctl output, so that the
    arbiter will be able to respond to requests coming from circusctl.
    """
    queue = Queue()
    circusctl_process = Process(target=run_ctl, args=(args, queue, stdin))
    circusctl_process.start()
    while queue.empty():
        yield tornado_sleep(.1)
    stderr = queue.get()
    stdout = queue.get()
    raise Return((stdout, stderr))


class CommandlineTest(TestCircus):

    def test_help_switch_no_command(self):
        stdout, stderr = run_ctl('--help')
        self.assertEqual(stderr, '')
        output = stdout.splitlines()
        self.assertEqual(output[0], 'usage: ' + USAGE)
        self.assertEqual(output[2], 'Controls a Circus daemon')
        self.assertEqual(output[4], 'Commands:')

    def test_help_invalid_command(self):
        stdout, stderr = run_ctl('foo')
        self.assertEqual(stdout, '')
        err = stderr.splitlines()
        self.assertEqual(err[0], 'usage: ' + USAGE)
        self.assertEqual(err[1],
                         'circusctl.py: error: unrecognized arguments: foo')

    def test_help_for_add_command(self):
        stdout, stderr = run_ctl('--help add')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout.splitlines()[0], 'Add a watcher')

    @gen_test
    def test_add(self):
        yield self.start_arbiter()
        poll_for(self.test_file, 'START')

        stdout, stderr = yield async_run_ctl('add test2 "sleep 1"')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'ok\n')

        stdout, stderr = yield async_run_ctl('status test2')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'stopped\n')
        yield self.stop_arbiter()

    @gen_test
    def test_add_start(self):
        yield self.start_arbiter()
        poll_for(self.test_file, 'START')

        stdout, stderr = yield async_run_ctl('add --start test2 "sleep 1"')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'ok\n')
        stdout, stderr = yield async_run_ctl('status test2')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'active\n')
        yield self.stop_arbiter()


class CLITest(TestCircus):

    @coroutine
    def run_ctl(self, command=''):
        """Send the given command to the CLI, and ends with EOF."""
        if command:
            command += '\n'
        stdout, stderr = yield async_run_ctl('', command + 'EOF\n')
        raise Return((stdout, stderr))

    @gen_test
    def test_launch_cli(self):
        yield self.start_arbiter()
        poll_for(self.test_file, 'START')

        stdout, stderr = yield self.run_ctl()
        self.assertEqual(stderr, '')
        output = stdout.splitlines()
        self.assertEqual(output[0], VERSION)
        # strip of term escape characters, if any
        prompt = output[2][-len(CircusCtl.prompt):]
        self.assertEqual(prompt, CircusCtl.prompt)

        yield self.stop_arbiter()

    def test_cli_help(self):
        stdout, stderr = yield self.run_ctl('help')
        self.assertEqual(stderr, '')
        prompt = stdout.splitlines()
        # first two lines are VERSION and prompt, followed by a blank line
        self.assertEqual(prompt[3], "Documented commands (type help <topic>):")
