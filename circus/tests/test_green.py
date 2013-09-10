from unittest2 import skipIf, TestCase

from gevent import monkey

from circus.green import get_arbiter
from circus.tests.test_arbiter import _TestTrainer
from circus.green.client import CircusClient
from circus.tests.support import has_gevent


@skipIf(not has_gevent(), 'Tests for Gevent')
class TestGreen(TestCase, _TestTrainer):
    @classmethod
    def setUpClass(cls):
        _TestTrainer.setUpClass()

    @classmethod
    def tearDownClass(cls):
        _TestTrainer.tearDownClass()

    @classmethod
    def _get_arbiter_factory(cls):
        monkey.patch_all()
        return get_arbiter

    @classmethod
    def _get_client_factory(cls):
        return CircusClient
