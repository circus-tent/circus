
import os
from circus.util import configure_logger
from circus import logger


_CONFIGURED = True
configure_logger(logger, level='DEBUG')

if not _CONFIGURED and 'TESTING' in os.environ:
    configure_logger(logger, level='CRITICAL', output="/dev/null")
    _CONFIGURED = True


def setUp():
    from circus import _patch   # NOQA
