import subprocess
import os
import sys
import time

from webtest import TestApp

from circus.tests.support import TestCircus
from circus.web.circushttpd import app
from circus.stream import QueueStream


cfg = os.path.join(os.path.dirname(__file__), 'test_web.ini')


class TestHttpd(TestCircus):
    def setUp(self):
        TestCircus.setUp(self)
        self.app = TestApp(app)
        self.stream = QueueStream()
        # let's run a circus
        cmd = '%s -c "from circus import circusd; circusd.main()" %s' % \
            (sys.executable, cfg)
        self.p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)

    def tearDown(self):
        self.p.terminate()
        self.p.kill()
        time.sleep(0.4)
        TestCircus.tearDown(self)

    def test_index(self):
        # let's open the web app
        res = self.app.get('/')

        # we have a form to connect to the current app
        res = res.form.submit()

        # that should be a 302, redirecting to the connected index
        # let's follow it
        res = res.follow()

        self.assertTrue('tcp://127.0.0.1:5557' in res.body)
