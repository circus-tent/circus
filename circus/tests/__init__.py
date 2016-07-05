import os
import zmq
from circus.util import configure_logger
from circus import logger


_CONFIGURED = False

if not _CONFIGURED and 'TESTING' in os.environ:
    configure_logger(logger, level='CRITICAL', output=os.devnull)
    _CONFIGURED = True


def setUp():
    from circus import _patch   # NOQA


def tearDown():
    # There seems to some issue with context cleanup and Python >= 3.4
    # making the tests hang at the end
    # Explicitely destroying the context seems to do the trick
    # cf https://github.com/zeromq/pyzmq/pull/513
    zmq.Context.instance().destroy()
