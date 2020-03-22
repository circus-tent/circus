import io
import sys


def sort_by_field(obj, field='name'):       # NOQA
    def _by_field(item):
        return item[field]

    obj.sort(key=_by_field)


def cast_bytes(s, encoding='utf8'):  # NOQA
    """cast unicode or bytes to bytes"""
    if isinstance(s, bytes):
        return s
    return str(s).encode(encoding)


def cast_unicode(s, encoding='utf8', errors='replace'):  # NOQA
    """cast bytes or unicode to unicode.
      errors options are strict, ignore or replace"""
    if isinstance(s, bytes):
        return s.decode(encoding, errors=errors)
    return str(s)


cast_string = cast_unicode


StringIO = io.StringIO      # NOQA
BytesIO = io.BytesIO        # NOQA


def raise_with_tb(E):     # NOQA
    raise E.with_traceback(sys.exc_info()[2])


def get_next(c):  # NOQA
    return c.__next__


MAXSIZE = sys.maxsize       # NOQA

b = cast_bytes
s = cast_string
u = cast_unicode
