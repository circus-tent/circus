import sys
import time

from circus.process import Process, RUNNING
from circus.tests.support import TestCircus


RLIMIT = '''\
import resource, sys

f = open(sys.argv[1], 'w')
for limit in ('NOFILE', 'NPROC'):
    res = getattr(resource, 'RLIMIT_%s' % limit)
    f.write('%s=%s\\n' % (limit, resource.getrlimit(res)))

f.close
'''


class TestProcess(TestCircus):

    def test_base(self):
        cmd = sys.executable
        args = "-c 'import time; time.sleep(2)'"
        process = Process('test', cmd, args=args, shell=True)
        try:
            info = process.info()
            self.assertEqual(process.pid, info['pid'])
            age = process.age()
            self.assertTrue(age > 0.)
            self.assertFalse(process.is_child(0))
        finally:
            process.stop()

    def test_rlimits(self):
        script_file = self.get_tmpfile(RLIMIT)
        output_file = self.get_tmpfile()

        cmd = sys.executable
        args = [script_file, output_file]
        rlimits = {'nofile': 20,
                   'nproc': 20}

        process = Process('test', cmd, args=args, rlimits=rlimits)
        # wait for the process to finish
        while process.status == RUNNING:
            time.sleep(1)

        f = open(output_file, 'r')
        output = {}
        for line in f.readlines():
            limit, value = line.rstrip().split('=', 1)
            output[limit] = value
        f.close()

        def srt2ints(val):
            return [long(key) for key in val[1:-1].split(',')]

        wanted = [20L, 20L]

        self.assertEqual(srt2ints(output['NOFILE']), wanted)
        self.assertEqual(srt2ints(output['NPROC']), wanted)
