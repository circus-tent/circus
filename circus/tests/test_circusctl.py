import subprocess
import sys
import shlex
from unittest import TestCase

from circus.circusctl import USAGE, VERSION, CircusCtl
from circus.tests.support import TestCircus


def run_ctl(args, stdin=''):
    cmd = '%s -m circus.circusctl' % sys.executable
    proc = subprocess.Popen(cmd.split() + shlex.split(args),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    return proc.communicate(stdin)


class CommandlineTest(TestCircus):
    def setUp(self):
        super(CommandlineTest, self).setUp()
        self._run_circus('circus.tests.support.run_process')

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

    def test_add(self):
        stdout, stderr = run_ctl('add test2 "sleep 1"')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'ok\n')
        stdout, stderr = run_ctl('status test2')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'stopped\n')

    def test_add_start(self):
        stdout, stderr = run_ctl('add --start test2 "sleep 1"')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'ok\n')
        stdout, stderr = run_ctl('status test2')
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'active\n')


class CLITest(TestCase):

    def run_ctl(self, command=''):
        """Send the given command to the CLI, and ends with EOF."""
        if command:
            command += '\n'
        return run_ctl('', command + 'EOF\n')

    def test_launch_cli(self):
        stdout, stderr = self.run_ctl()
        self.assertEqual(stderr, '')
        output = stdout.splitlines()
        self.assertEqual(output[0], VERSION)
        # strip of term escape characters, if any
        prompt = output[1][-len(CircusCtl.prompt):]
        self.assertEqual(prompt, CircusCtl.prompt)

    def test_cli_help(self):
        stdout, stderr = self.run_ctl('help')
        self.assertEqual(stderr, '')
        prompt = stdout.splitlines()
        # first two lines are VERSION and prompt, followed by a blank line
        self.assertEqual(prompt[2], "Documented commands (type help <topic>):")
