from unittest2 import skipIf, TestCase

from circus.green import get_arbiter
from circus.tests.test_arbiter import _TestTrainer, _setUpClass, _tearDownClass
from circus.tests.support import has_gevent


@skipIf(not has_gevent(), 'Tests for Gevent')
class TestGreen(TestCase, _TestTrainer):
    @classmethod
    def setUpClass(cls):
        _setUpClass(cls, factory=cls._get_arbiter_factory(),
                    client_factory=cls._get_client_factory())

    @classmethod
    def tearDownClass(cls):
        _tearDownClass(cls)

    @classmethod
    def _get_arbiter_factory(cls):
        from gevent import monkey
        monkey.patch_all()
        return get_arbiter

    @classmethod
    def _get_client_factory(cls):
        from circus.green.client import CircusClient
        return CircusClient
