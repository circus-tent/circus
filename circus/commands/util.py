from circus.exc import ArgumentError, MessageError
from circus.py3compat import string_types
from circus import util
import warnings


def convert_option(key, val):
    if key == "numprocesses":
        return int(val)
    elif key == "warmup_delay":
        return float(val)
    elif key == "working_dir":
        return val
    elif key == "uid":
        return val
    elif key == "gid":
        return val
    elif key == "send_hup":
        return util.to_bool(val)
    elif key == "shell":
        return util.to_bool(val)
    elif key == "copy_env":
        return util.to_bool(val)
    elif key == "env":
        return util.parse_env_dict(val)
    elif key == "cmd":
        return val
    elif key == "flapping_attempts":
        return int(val)
    elif key == "flapping_window":
        return float(val)
    elif key == "retry_in":
        return float(val)
    elif key == "max_retry":
        return int(val)
    elif key == "graceful_timeout":
        return float(val)
    elif key == 'max_age':
        return int(val)
    elif key == 'max_age_variance':
        return int(val)
    elif key == 'respawn':
        return util.to_bool(val)
    elif key.startswith('stderr_stream.') or key.startswith('stdout_stream.'):
        subkey = key.split('.', 1)[-1]
        if subkey in ('max_bytes', 'backup_count'):
            return int(val)
        return val
    raise ArgumentError("unknown key %r" % key)


def validate_option(key, val):
    valid_keys = ('numprocesses', 'warmup_delay', 'working_dir', 'uid',
                  'gid', 'send_hup', 'shell', 'env', 'cmd', 'copy_env',
                  'flapping_attempts', 'flapping_window', 'retry_in',
                  'max_retry', 'graceful_timeout', 'stdout_stream',
                  'stderr_stream', 'max_age', 'max_age_variance', 'respawn',
                  'hooks')
    valid_prefixes = ('stdout_stream', 'stderr_stream', 'hooks')

    def _valid_prefix():
        for prefix in valid_prefixes:
            if key.startswith('%s.' % prefix):
                return True
        return False

    if key not in valid_keys and not _valid_prefix():
        raise MessageError('unknown key %r' % key)

    if key in ('numprocesses', 'flapping_attempts', 'max_retry', 'max_age',
               'max_age_variance'):
        if not isinstance(val, int):
            raise MessageError("%r isn't an integer" % key)

    if key in ('warmup_delay', 'flapping_window', 'retry_in',
               'graceful_timeout',):
        if not isinstance(val, (int, float,)):
            raise MessageError("%r isn't a number" % key)

    if key in ('uid', 'gid',):
        if not isinstance(val, int) and not isinstance(val, string_types):
            raise MessageError("%r isn't an integer or string" % key)

    if key in ('send_hup', 'shell', 'copy_env', 'respawn'):
        if not isinstance(val, bool):
            raise MessageError("%r isn't a valid boolean" % key)

    if key in ('env', ):
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid object" % key)

        for k, v in val.items():
            if not isinstance(v, string_types):
                raise MessageError("%r isn't a string" % k)

    if key in ('stderr_stream', 'stdout_stream'):
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid object" % key)
        if not 'class' in val:
            raise MessageError("%r must have a 'class' key" % key)
        if 'refresh_time' in val:
            warnings.warn(u"'refresh_time' is deprecated and not useful "
                          u"anymore for %r" % key)
