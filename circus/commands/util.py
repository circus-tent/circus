from circus.exc import ArgumentError, MessageError
from circus import util
import warnings
try:
    import resource
except ImportError:
    resource = None     # NOQA

_HOOKS = ('before_start', 'after_start', 'before_stop', 'after_stop',
          'before_spawn', 'after_spawn', 'before_signal', 'after_signal',
          'before_reap', 'after_reap', 'extended_stats')


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
    elif key == "stop_signal":
        return util.to_signum(val)
    elif key == "stop_children":
        return util.to_bool(val)
    elif key == "shell":
        return util.to_bool(val)
    elif key == "copy_env":
        return util.to_bool(val)
    elif key == "env":
        return util.parse_env_dict(val)
    elif key == "cmd":
        return val
    elif key == "args":
        return val
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
    elif key == "singleton":
        return util.to_bool(val)
    elif key == "close_child_stdin":
        return util.to_bool(val)
    elif key == "close_child_stdout":
        return util.to_bool(val)
    elif key == "close_child_stderr":
        return util.to_bool(val)
    elif key == "use_papa":
        return util.to_bool(val)
    elif key.startswith('stderr_stream.') or key.startswith('stdout_stream.'):
        subkey = key.split('.', 1)[-1]
        if subkey in ('max_bytes', 'backup_count'):
            return int(val)
        return val
    elif key == 'hooks':
        res = {}
        for hook in val.split(','):
            if hook == '':
                continue
            hook = hook.split(':')
            if len(hook) != 2:
                raise ArgumentError(hook)

            name, value = hook
            if name not in _HOOKS:
                raise ArgumentError(name)

            res[name] = value

        return res
    elif key.startswith('hooks.'):
        # we can also set a single hook
        name = key.split('.', 1)[-1]
        if name not in _HOOKS:
            raise ArgumentError(name)
        return val
    elif key.startswith('rlimit_'):
        return int(val)

    raise ArgumentError("unknown key %r" % key)


def validate_option(key, val):
    valid_keys = ('numprocesses', 'warmup_delay', 'working_dir', 'uid',
                  'gid', 'send_hup', 'stop_signal', 'stop_children',
                  'shell', 'env', 'cmd', 'args', 'copy_env', 'retry_in',
                  'max_retry', 'graceful_timeout', 'stdout_stream',
                  'stderr_stream', 'max_age', 'max_age_variance', 'respawn',
                  'singleton', 'hooks', 'close_child_stdin',
                  'close_child_stdout', 'close_child_stderr', 'use_papa')

    valid_prefixes = ('stdout_stream.', 'stderr_stream.', 'hooks.', 'rlimit_')

    def _valid_prefix():
        for prefix in valid_prefixes:
            if key.startswith('%s' % prefix):
                return True
        return False

    if key not in valid_keys and not _valid_prefix():
        raise MessageError('unknown key %r' % key)

    if key in ('numprocesses', 'max_retry', 'max_age', 'max_age_variance',
               'stop_signal'):
        if not isinstance(val, int):
            raise MessageError("%r isn't an integer" % key)

    elif key in ('warmup_delay', 'retry_in', 'graceful_timeout',):
        if not isinstance(val, (int, float)):
            raise MessageError("%r isn't a number" % key)

    elif key in ('uid', 'gid',):
        if not isinstance(val, int) and not isinstance(val, str):
            raise MessageError("%r isn't an integer or string" % key)

    elif key in ('send_hup', 'shell', 'copy_env', 'respawn', 'stop_children',
                 'close_child_stdin', 'close_child_stdout',
                 'close_child_stderr'):
        if not isinstance(val, bool):
            raise MessageError("%r isn't a valid boolean" % key)

    elif key in ('env', ):
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid object" % key)

        for k, v in val.items():
            if not isinstance(v, str):
                raise MessageError("%r isn't a string" % k)

    elif key == 'hooks':
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid hook dict" % val)

        for key in val:
            if key not in _HOOKS:
                raise MessageError("Unknown hook %r" % val)

    elif key in ('stderr_stream', 'stdout_stream'):
        if not isinstance(val, dict):
            raise MessageError("%r isn't a valid object" % key)
        if 'class' not in val:
            raise MessageError("%r must have a 'class' key" % key)
        if 'refresh_time' in val:
            warnings.warn("'refresh_time' is deprecated and not useful "
                          "anymore for %r" % key)

    elif key.startswith('rlimit_'):
        if resource:
            rlimit_key = key[7:]
            rlimit_int = getattr(
                resource, 'RLIMIT_' + rlimit_key.upper(), None
            )
            if rlimit_int is None:
                raise MessageError("%r isn't a valid rlimit setting" % key)
        else:
            raise MessageError("rlimit options are not supported on this"
                               " platform")

        # note that a null val means RLIM_INFINITY
        if val is not None and not isinstance(val, int):
            raise MessageError("%r rlimit value isn't a valid int" % val)
