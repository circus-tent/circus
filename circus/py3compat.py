import sys

PY3 = sys.version_info[0] >= 3

if PY3:
    import collections
    string_types = str
    integer_types = int
    text_type = str
    long = int

    def bytestring(s):  # NOQA
        return s

    import io
    StringIO = io.StringIO      # NOQA
    BytesIO = io.BytesIO        # NOQA

    def raise_with_tb(E):     # NOQA
        raise E.with_traceback(sys.exc_info()[2])

    def is_callable(c):
        return isinstance(c, collections.Callable)

    def get_next(c):
        return c.__next__

    MAXSIZE = sys.maxsize       # NOQA
else:
    string_types = basestring  # NOQA
    integer_types = (int, long)
    text_type = unicode  # NOQA
    long = long

    def bytestring(s):  # NOQA
        if isinstance(s, unicode):  # NOQA
            return s.encode('utf-8')
        return s

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
