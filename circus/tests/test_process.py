import unittest
import os
import sys
import tempfile
import time
from circus.process import Process, RUNNING


class TestProcess(unittest.TestCase):

    def test_base(self):
        cmd = "%s -c 'import time; time.sleep(2)'"
        process = Process('test', cmd % sys.executable, shell=True)
        try:
            info = process.info()
            self.assertEqual(process.pid, info['pid'])
            age = process.age()
            self.assertTrue(age > 0.)
            self.assertFalse(process.is_child(0))
        finally:
            process.stop()

    def test_rlimits(self):
        script_file = tempfile.mkstemp()[1]
        output_file = tempfile.mkstemp()[1]
        script = '''
import resource, sys
f = open(sys.argv[1], 'w')
for limit in ('NOFILE', 'NPROC'):
    res = getattr(resource, 'RLIMIT_%s' % limit)
    f.write('%s=%s\\n' % (limit, resource.getrlimit(res)))
f.close
        '''
        f = open(script_file, 'w')
        f.write(script)
        f.close()
        cmd = '%s %s %s' % (sys.executable, script_file, output_file)
        rlimits = {'nofile': 20,
                   'nproc': 20,
                  }
        process = Process('test', cmd, rlimits=rlimits)
        # wait for the process to finish
        while process.status == RUNNING:
            time.sleep(1)

        f = open(output_file, 'r')
        output = {}
        for line in f.readlines():
            (limit, value) = line.rstrip().split('=', 1)
            output[limit] = value
        f.close()

        try:
            self.assertEqual(output['NOFILE'], '(20, 20)')
            self.assertEqual(output['NPROC'], '(20, 20)')
        finally:
            os.unlink(script_file)
            os.unlink(output_file)
