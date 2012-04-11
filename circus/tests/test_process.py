import unittest
import os
import sys
import tempfile
import time
import StringIO

from circus.process import Process, RUNNING


RLIMIT = '''\
import resource, sys

f = open(sys.argv[1], 'w')
for limit in ('NOFILE', 'NPROC'):
    res = getattr(resource, 'RLIMIT_%s' % limit)
    f.write('%s=%s\\n' % (limit, resource.getrlimit(res)))

f.close
'''

STREAM = """\
import time
import os
import sys

i = 0

while True:
    sys.stdout.write('%d-%s\\n' % (os.getpid(), i))
    sys.stdout.flush()
    i += 1
    time.sleep(0.1)

"""


class TestProcess(unittest.TestCase):

    def setUp(self):
        self.files = []

    def tearDown(self):
        for file in self.files:
            if os.path.exists(file):
                os.remove(file)

    def get_tmpfile(self, content=None):
        fd, file = tempfile.mkstemp()
        os.close(fd)
        self.files.append(file)
        if content is not None:
            with open(file, 'w') as f:
                f.write(content)
        return file

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

    def test_streams(self):
        try:
            import gevent
        except ImportError:
            return

        from gevent.queue import Queue

        script_file = self.get_tmpfile(STREAM)

        class StreamQueue(Queue):
            def write(self, data):
                self.put(data)

        stream = StreamQueue()

        cmd = sys.executable
        args = [script_file]

        process = Process('test', cmd, args=args, stdout_stream=stream,
                          stderr_stream=stream)

        time.sleep(2.)

        # stop it
        process.stop()

        # let's see what we got
        self.assertTrue(stream.qsize() > 10)
