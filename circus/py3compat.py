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


b = cast_bytes
s = cast_string
u = cast_unicode
