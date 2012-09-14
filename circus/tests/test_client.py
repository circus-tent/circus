import os
import subprocess
import time

from circus.tests.support import TestCircus
from circus.client import CircusClient, make_message

SSH_PATH = '/home/' + os.getlogin() + '/.ssh/'
SSH_ID_DSA = SSH_PATH + 'id_dsa'
SSH_ID_DSA_PUB = SSH_PATH + 'id_dsa.pub'
SSH_AUTHORIZED_KEYS = SSH_PATH + 'authorized_keys'
COPY_ID_DSA = 'circus/tests/id_dsa'
COPY_ID_DSA_PUB = 'circus/tests/id_dsa.pub'
COPY_AUTHORIZED_KEYS = 'circus/tests/authorized_keys'


class TestClient(TestCircus):

    def setUp(self):
        TestCircus.setUp(self)

        return
        # XXX to be fixed
        subprocess.call(['mv', SSH_ID_DSA, COPY_ID_DSA])
        subprocess.call(['mv', SSH_ID_DSA_PUB, COPY_ID_DSA_PUB])
        subprocess.call(['mv', SSH_AUTHORIZED_KEYS, COPY_AUTHORIZED_KEYS])
        subprocess.call(['cp', 'circus/tests/test_dsa', SSH_ID_DSA])
        subprocess.call(['cp', 'circus/tests/test_dsa.pub', SSH_ID_DSA_PUB])
        subprocess.call(['cp', 'circus/tests/test_dsa.pub',
                            SSH_AUTHORIZED_KEYS])
        subprocess.call(['ssh-add'])

    def tearDown(self):
        TestCircus.tearDown(self)

        return

        # XXX to be fixed
        subprocess.call(['rm', SSH_ID_DSA])
        subprocess.call(['rm', SSH_ID_DSA_PUB])
        subprocess.call(['rm', SSH_AUTHORIZED_KEYS])
        subprocess.call(['mv', COPY_ID_DSA, SSH_ID_DSA])
        subprocess.call(['mv', COPY_ID_DSA_PUB, SSH_ID_DSA_PUB])
        subprocess.call(['mv', COPY_AUTHORIZED_KEYS, SSH_AUTHORIZED_KEYS])
        subprocess.call(['ssh-add'])

    def _client_test(self, ssh_server):
        self._run_circus('circus.tests.support.run_process')
        time.sleep(.5)

        # playing around with the watcher
        client = CircusClient(ssh_server=ssh_server)

        def call(cmd, **props):
            msg = make_message(cmd, **props)
            return client.call(msg)

        def status(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('status')

        def numprocesses(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('numprocesses')

        def numwatchers(cmd, **props):
            resp = call(cmd, **props)
            return resp.get('numwatchers')

        def set(name, **opts):
            return status("set", name=name, options=opts)

        self.assertEquals(set("test", numprocesses=10), 'ok')
        self.assertEquals(numprocesses("numprocesses"), 10)
        self.assertEquals(set("test", numprocesses=1), 'ok')
        self.assertEquals(numprocesses("numprocesses"), 1)
        self.assertEquals(numwatchers("numwatchers"), 1)

        self.assertEquals(call("list").get('watchers'), ['test'])
        self.assertEquals(numprocesses("incr", name="test"), 2)
        self.assertEquals(numprocesses("numprocesses"), 2)
        self.assertEquals(numprocesses("incr", name="test", nb=2), 4)
        self.assertEquals(numprocesses("decr", name="test", nb=3), 1)
        self.assertEquals(numprocesses("numprocesses"), 1)
        self.assertEquals(set("test", env={"test": 1, "test": 2}), 'error')
        self.assertEquals(set("test", env={"test": '1', "test": '2'}),
                'ok')
        resp = call('get', name='test', keys=['env'])
        options = resp.get('options', {})

        self.assertEquals(options.get('env'), {'test': '1', 'test': '2'})

        resp = call('stats', name='test')
        self.assertEqual(resp['status'], 'ok')

        resp = call('globaloptions', name='test')
        self.assertEqual(resp['options']['pubsub_endpoint'],
                        'tcp://127.0.0.1:5556')
        client.stop()

    def XXX_test_handler(self):
        self._client_test(None)

    def XXX_test_handler_ssh(self):
        try:
            try:
                import pexpect    # NOQA
            except ImportError:
                import paramiko   # NOQA
        except ImportError:
            return
        self._client_test('localhost')
