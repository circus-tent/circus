import sys

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str
    integer_types = int
    text_type = str

    def b2s(s):     # NOQA
        return s.decode('latin1')

    def s2b(s):     # NOQA
        return s.encode('latin1')

    def bytestring(s):  # NOQA
        return s

    import io
    StringIO = io.StringIO      # NOQA
    BytesIO = io.BytesIO        # NOQA

    def raise_with_tb(E, V, T):     # NOQA
        raise E(V).with_traceback(T)

    MAXSIZE = sys.maxsize       # NOQA
else:
    string_types = basestring,
    integer_types = (int, long)
    text_type = unicode

    def b2s(s):     # NOQA
        return s

    def s2b(s):     # NOQA
        return s

    def bytestring(s):  # NOQA
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    try:
        import cStringIO
        StringIO = cStringIO.StringIO   # NOQA
    except ImportError:
        import StringIO
        StringIO = StringIO.StringIO    # NOQA

    BytesIO = StringIO

    def raise_with_tb(E, V, T):     # NOQA
        raise E, V, T

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
