import os
import subprocess
import time
import zmq

from circus.tests.support import TestCircus
from circus.client import CircusClient, make_message


def run_process(test_file):
    try:
        while True:
            time.sleep(1)
    except:
        return 1


class TestClient(TestCircus):

    def setUp(self):
        TestCircus.setUp(self)

    def tearDown(self):
        TestCircus.tearDown(self)
        if hasattr(self, 'client'):
            self.client.stop()
        if hasattr(self, 'config'):
            os.remove(self.config)

    def _client_test(self, ssh_server=None, keyfile=None):
        self._run_circus('circus.tests.test_client.run_process')
        time.sleep(.5)

        # playing around with the watcher
        self.client = CircusClient(ssh_server=ssh_server, keyfile=keyfile)

        def call(cmd, **props):
            msg = make_message(cmd, **props)
            return self.client.call(msg)

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

    def test_handler(self):
        self._client_test()

    def test_handler_ssh(self):
        def get_test_directory():
            return os.path.join(os.getcwd(), 'circus/tests/')
        try:
            try:
                import pexpect    # NOQA
            except ImportError:
                import paramiko   # NOQA
        except ImportError:
            return
        port = zmq.ssh.tunnel.select_random_ports(1)[0]
        self.config = get_test_directory() + 'sshd_config'
        config = self.config
        config_template = config + '_template'
        config_file = open(config, 'w')
        config_template_file = open(config_template)
        for line in config_template_file:
            config_file.write(line.replace('FOLDER', get_test_directory()))
        config_file.close()
        config_template_file.close()
        os.system('/usr/sbin/sshd -p ' + str(port) + ' -f ' + config)
        keyfile = get_test_directory() + 'key_dsa'
        self._client_test(ssh_server='localhost -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no:' + str(port), keyfile=keyfile)
