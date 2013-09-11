from unittest2 import skipIf

from circus.tests.support import has_gevent
from circus.green import get_arbiter
from circus.tests.test_arbiter import TestTrainer


@skipIf(not has_gevent(), 'Tests for Gevent')
class TestGreen(TestTrainer):
    arbiter_factory = get_arbiter
