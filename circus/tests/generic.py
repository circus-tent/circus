import sys

sys.path.insert(0, './')


def resolve_name(name):
    ret = None
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]
    last_exc = None

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError as exc:
            last_exc = exc
            if cursor == 0:
                raise
            cursor -= 1
            module_name = parts[:cursor]

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError:
            if last_exc is not None:
                raise last_exc
            raise ImportError(name)

    if ret is None:
        if last_exc is not None:
            raise last_exc
        raise ImportError(name)

    return ret


if __name__ == '__main__':
    callback = resolve_name(sys.argv[1])
    try:
        if len(sys.argv) > 2:
            test_file = sys.argv[2]
            sys.exit(callback(test_file))
        else:
            sys.exit(callback())
    except:  # noqa: E722
        sys.exit(1)
