import subprocess
import sys
import time

from circus.tests.support import TestCircus

USAGE = 'usage: circusctl.py [options] command [args]'


class TestCommandline(TestCircus):
    def setUp(self):
        super(TestCommandline, self).setUp()
        self.dummy_process = 'circus.tests.test_arbiter.run_dummy'
        self.test_file = self._run_circus(self.dummy_process)

    def run_ctl(self, args):
        cmd = '%s -m circus.circusctl' % sys.executable
        proc = subprocess.Popen(cmd.split() + args.split(),
                                stdout=subprocess.PIPE)
        # use proc.communicate, if we need to handle lots of output
        while proc.returncode is None:
            time.sleep(0.1)
            proc.poll()

        return proc.stdout.read().strip()

    def test_help_no_command(self):
        output = self.run_ctl('').splitlines()
        self.assertEqual(output[0], USAGE)
        self.assertEqual(output[2], 'Controls a Circus daemon')
        self.assertEqual(output[4], 'Commands:')

    def test_help_switch_no_command(self):
        output = self.run_ctl('--help').splitlines()
        self.assertEqual(output[0], USAGE)
        self.assertEqual(output[2], 'Controls a Circus daemon')
        self.assertEqual(output[4], 'Commands:')

    def test_help_invalid_command(self):
        output = self.run_ctl('').splitlines()
        self.assertEqual(output[0], USAGE)

    def test_help_for_add_command(self):
        output = self.run_ctl('add --help').splitlines()
        self.assertEqual(output[0], 'Add a watcher')
