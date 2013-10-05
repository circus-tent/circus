import sys


def raise_with_tb(E):     # NOQA
    raise E, None, sys.exc_info()[2]
