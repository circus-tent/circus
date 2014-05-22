import os
import sys

from circus.process import Process
from circus.tests.support import (TestCircus, skipIf, EasyTestSuite, DEBUG,
                                  poll_for)
import circus.py3compat
from circus.py3compat import StringIO, PY2


RLIMIT = """\
import resource, sys

try:
    with open(sys.argv[1], 'w') as f:
        for limit in ('NOFILE', 'NPROC'):
            res = getattr(resource, 'RLIMIT_%s' % limit)
            f.write('%s=%s\\n' % (limit, resource.getrlimit(res)))
        f.write('END')
finally:
    sys.exit(0)
"""


VERBOSE = """\
import sys

try:
    for i in range(1000):
        for stream in (sys.stdout, sys.stderr):
            stream.write(str(i))
            stream.flush()
    with open(sys.argv[1], 'w') as f:
        f.write('END')
finally:
    sys.exit(0)

"""


def _nose_no_s():
    if PY2:
        return not hasattr(sys.stdout, 'fileno')
    else:
        return isinstance(sys.stdout, StringIO)


class TestProcess(TestCircus):

    def test_base(self):
        cmd = sys.executable
        args = "-c 'import time; time.sleep(2)'"
        process = Process('test', cmd, args=args, shell=False)
        try:
            info = process.info()
            self.assertEqual(process.pid, info['pid'])
            age = process.age()
            self.assertTrue(age > 0.)
            self.assertFalse(process.is_child(0))
        finally:
            process.stop()

    @skipIf(DEBUG, 'Py_DEBUG=1')
    def test_rlimits(self):
        script_file = self.get_tmpfile(RLIMIT)
        output_file = self.get_tmpfile()

        cmd = sys.executable
        args = [script_file, output_file]
        rlimits = {'nofile': 20,
                   'nproc': 20}

        process = Process('test', cmd, args=args, rlimits=rlimits)
        poll_for(output_file, 'END')
        process.stop()

        with open(output_file, 'r') as f:
            output = {}
            for line in f.readlines():
                line = line.rstrip()
                line = line.split('=', 1)
                if len(line) != 2:
                    continue
                limit, value = line
                output[limit] = value

        def srt2ints(val):
            return [circus.py3compat.long(key) for key in val[1:-1].split(',')]

        wanted = [circus.py3compat.long(20), circus.py3compat.long(20)]

        self.assertEqual(srt2ints(output['NOFILE']), wanted)
        self.assertEqual(srt2ints(output['NPROC']), wanted)

    def test_comparison(self):
        cmd = sys.executable
        args = ['import time; time.sleep(2)', ]
        p1 = Process('1', cmd, args=args)
        p2 = Process('2', cmd, args=args)

        self.assertTrue(p1 < p2)
        self.assertFalse(p1 == p2)
        self.assertTrue(p1 == p1)

        p1.stop()
        p2.stop()

    def test_process_parameters(self):
        # all the options passed to the process should be available by the
        # command / process

        p1 = Process('1', 'make-me-a-coffee',
                     '$(circus.wid) --type $(circus.env.type)',
                     shell=False, spawn=False, env={'type': 'macchiato'})

        self.assertEqual(['make-me-a-coffee', '1', '--type', 'macchiato'],
                         p1.format_args())

        p2 = Process('1', 'yeah $(CIRCUS.WID)', spawn=False)
        self.assertEqual(['yeah', '1'], p2.format_args())

        os.environ['coffee_type'] = 'american'
        p3 = Process('1', 'yeah $(circus.env.type)', shell=False, spawn=False,
                     env={'type': 'macchiato'})
        self.assertEqual(['yeah', 'macchiato'], p3.format_args())
        os.environ.pop('coffee_type')

    @skipIf(DEBUG, 'Py_DEBUG=1')
    @skipIf(_nose_no_s(), 'Nose runs without -s')
    def test_streams(self):
        script_file = self.get_tmpfile(VERBOSE)
        output_file = self.get_tmpfile()

        cmd = sys.executable
        args = [script_file, output_file]

        # 1. streams sent to /dev/null
        process = Process('test', cmd, args=args, close_child_stdout=True,
                          close_child_stderr=True)
        try:
            poll_for(output_file, 'END')

            # the pipes should be empty
            self.assertEqual(process.stdout.read(), b'')
            self.assertEqual(process.stderr.read(), b'')
        finally:
            process.stop()

        # 2. streams sent to /dev/null, no PIPEs
        output_file = self.get_tmpfile()
        args[1] = output_file

        process = Process('test', cmd, args=args, close_child_stdout=True,
                          close_child_stderr=True, pipe_stdout=False,
                          pipe_stderr=False)

        try:
            poll_for(output_file, 'END')
            # the pipes should be unexistant
            self.assertTrue(process.stdout is None)
            self.assertTrue(process.stderr is None)
        finally:
            process.stop()

        # 3. streams & pipes open
        output_file = self.get_tmpfile()
        args[1] = output_file
        process = Process('test', cmd, args=args)

        try:
            poll_for(output_file, 'END')

            # the pipes should be unexistant
            self.assertEqual(len(process.stdout.read()), 2890)
            self.assertEqual(len(process.stderr.read()), 2890)
        finally:
            process.stop()

    def test_initgroups(self):
        cmd = sys.executable
        args = ['import time; time.sleep(2)']
        gid = os.getgid()
        uid = os.getuid()
        p1 = Process('1', cmd, args=args, gid=gid, uid=uid)
        p1.stop()


test_suite = EasyTestSuite(__name__)
