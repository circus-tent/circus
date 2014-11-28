import sys

PY2 = sys.version_info[0] < 3

if PY2:
    string_types = basestring  # NOQA
    integer_types = (int, long)  # NOQA
    text_type = unicode  # NOQA
    long = long  # NOQA
    bytes = str

    def bytestring(s):  # NOQA
        if isinstance(s, unicode):  # NOQA
            return s.encode('utf-8')
        return s

    def cast_bytes(s, encoding='utf8'):
        """cast unicode or bytes to bytes"""
        if isinstance(s, unicode):
            return s.encode(encoding)
        return str(s)

    def cast_unicode(s, encoding='utf8', errors='replace'):
        """cast bytes or unicode to unicode.
          errors options are strict, ignore or replace"""
        if isinstance(s, unicode):
            return s
        return str(s).decode(encoding)

    def cast_string(s, errors='replace'):
        return s if isinstance(s, basestring) else str(s)  # NOQA

    try:
        import cStringIO
        StringIO = cStringIO.StringIO   # NOQA
    except ImportError:
        import StringIO
        StringIO = StringIO.StringIO    # NOQA

    BytesIO = StringIO

    eval(compile('def raise_with_tb(E): raise E, None, sys.exc_info()[2]',
                 'py3compat.py', 'exec'))

    def is_callable(c):  # NOQA
        return callable(c)

    def get_next(c):  # NOQA
        return c.next

    # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
    class X(object):
        def __len__(self):
            return 1 << 31
    try:
        len(X())
    except OverflowError:
        # 32-bit
        MAXSIZE = int((1 << 31) - 1)        # NOQA
    else:
        # 64-bit
        MAXSIZE = int((1 << 63) - 1)        # NOQA
    del X

    def sort_by_field(obj, field='name'):   # NOQA
        def _by_field(item1, item2):
            return cmp(item1[field], item2[field])  # NOQA

        obj.sort(_by_field)

else:
    import collections
    string_types = str
    integer_types = int
    text_type = str
    long = int
    unicode = str

    def sort_by_field(obj, field='name'):       # NOQA
        def _by_field(item):
            return item[field]

        obj.sort(key=_by_field)

    def bytestring(s):  # NOQA
        return s

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

    import io
    StringIO = io.StringIO      # NOQA
    BytesIO = io.BytesIO        # NOQA

    def raise_with_tb(E):     # NOQA
        raise E.with_traceback(sys.exc_info()[2])

    def is_callable(c):  # NOQA
        return isinstance(c, collections.Callable)

    def get_next(c):  # NOQA
        return c.__next__

    MAXSIZE = sys.maxsize       # NOQA

b = cast_bytes
s = cast_string
u = cast_unicode

try:
    # PY >= 3.3
    from shlex import quote  # NOQA
except ImportError:
    from pipes import quote  # NOQA
