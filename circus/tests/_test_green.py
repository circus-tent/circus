from circus.tests.support import has_gevent, skipIf
from circus.green import get_arbiter
from circus.tests.test_arbiter import TestTrainer, EasyTestSuite


@skipIf(not has_gevent(), 'Tests for Gevent')
class TestGreen(TestTrainer):
    arbiter_factory = get_arbiter

test_suite = EasyTestSuite(__name__)
