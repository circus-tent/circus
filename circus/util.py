from datetime import timedelta
import grp
import os
import pwd
import fcntl
from functools import wraps
import sys
import shlex

from psutil.error import AccessDenied, NoSuchProcess
from circus import logger


try:
    from importlib import import_module         # NOQA
except ImportError:
    def _resolve_name(name, package, level):
        """Returns the absolute name of the module to be imported. """
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in xrange(level, 1, -1):
            try:
                dot = package.rindex('.', 0, dot)
            except ValueError:
                raise ValueError("attempted relative import beyond top-level "
                                  "package")
        return "%s.%s" % (package[:dot], name)


    def import_module(name, package=None):      # NOQA
        """Import a module.
        The 'package' argument is required when performing a relative import.
        It specifies the package to use as the anchor point from which to
        resolve the relative import to an absolute import."""
        if name.startswith('.'):
            if not package:
                raise TypeError("relative imports require the 'package' "
                                "argument")
            level = 0
            for character in name:
                if character != '.':
                    break
                level += 1
            name = _resolve_name(name[level:], package, level)
        __import__(name)
        return sys.modules[name]

try:
    from setproctitle import setproctitle
    def _setproctitle(title):       # NOQA
        setproctitle(title)
except ImportError:
    def _setproctitle(title):       # NOQA
        return


_SYMBOLS = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')


def get_working_dir():
    """Returns current path, try to use PWD env first"""
    try:
        a = os.stat(os.environ['PWD'])
        b = os.stat(os.getcwd())
        if a.ino == b.ino and a.dev == b.dev:
            working_dir = os.environ['PWD']
        else:
            working_dir = os.getcwd()
    except:
        working_dir = os.getcwd()
    return working_dir


def bytes2human(n):
    """Translates bytes into a human repr.
    """
    if not isinstance(n, int):
        raise TypeError(n)

    prefix = {}
    for i, s in enumerate(_SYMBOLS):
        prefix[s] = 1 << (i + 1) * 10

    for s in reversed(_SYMBOLS):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n


def get_info(process):
    info = {}
    try:
        mem_info = process.get_memory_info()
        info['mem_info1'] = bytes2human(mem_info[0])
        info['mem_info2'] = bytes2human(mem_info[1])
    except AccessDenied:
        info['mem_info1'] = info['mem_info2'] = "N/A"

    try:
        info['cpu'] = process.get_cpu_percent(interval=0)
    except AccessDenied:
        info['cpu'] = "N/A"

    try:
        info['mem'] = round(process.get_memory_percent(), 1)
    except AccessDenied:
        info['mem'] = "N/A"

    try:
        cpu_times = process.get_cpu_times()
        ctime = timedelta(seconds=sum(cpu_times))
        ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                        str((ctime.seconds % 60)).zfill(2),
                        str(ctime.microseconds)[:2])
    except AccessDenied:
        ctime = "N/A"

    info['ctime'] = ctime

    try:
        info['pid'] = process.pid
    except AccessDenied:
        info['pid'] = 'N/A'

    try:
        info['username'] = process.username
    except AccessDenied:
        info['username'] = 'N/A'

    try:
        info['nice'] = process.nice
    except AccessDenied:
        info['nice'] = 'N/A'
    except NoSuchProcess:
        info['nice'] = 'Zombie'

    try:
        cmdline = os.path.basename(shlex.split(process.cmdline[0])[0])
    except (AccessDenied, IndexError):
        cmdline = "N/A"

    info['cmdline'] = cmdline

    return info


def to_bool(s):
    if s.lower().strip() in ("true", "1",):
        return True
    elif s.lower().strip() in ("false", "0"):
        return False
    else:
        raise ValueError("%r is not a boolean" % s)


def to_uid(name):
    """Return an uid, given a user name.
    If the name is an integer, make sure it's an existing uid.

    If the user name is unknown, raises a ValueError.
    """
    if isinstance(name, int):
        try:
            pwd.getpwuid(name)
            return name
        except (KeyError, OverflowError):
            raise ValueError("%r isn't a valid user id" % name)

    if not isinstance(name, str):
        raise TypeError(name)

    try:
        return pwd.getpwnam(name).pw_uid
    except KeyError:
        raise ValueError("%r isn't a valid user name" % name)


def to_gid(name):
    """Return a gid, given a group name

    If the group name is unknown, raises a ValueError.
    """
    if isinstance(name, int):
        try:
            grp.getgrgid(name)
            return name
        except (KeyError, OverflowError):
            raise ValueError("No such group: %r" % name)

    if not isinstance(name, str):
        raise TypeError(name)
    try:
        return grp.getgrnam(name).gr_gid
    except KeyError:
        raise ValueError("No such group: %r" % name)


def parse_env(env_str):
    env = {}
    for kvs in env_str.split(","):
        k, v = kvs.split("=")
        env[k.strip()] = v.strip()
    return env


def env_to_str(env):
    if not env:
        return ""
    return ",".join(["%s=%s" % (k, v) for k, v in env.items()])


def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def debuglog(func):
    @wraps(func)
    def _log(self, *args, **kw):
        if os.environ.get('DEBUG') is None:
            return func(self, *args, **kw)

        cls = self.__class__.__name__
        logger.debug("'%s.%s' starts" % (cls, func.func_name))
        try:
            return func(self, *args, **kw)
        finally:
            logger.debug("'%s.%s' ends" % (cls, func.func_name))

    return _log


def convert_opt(key, val):
    """ get opt
    """
    if key == "env":
        val = env_to_str(val)
    else:
        if val is None:
            val = ""
        else:
            val = str(val)
    return val


# taken from distutils2
def resolve_name(name):
    """Resolve a name like ``module.object`` to an object and return it.

    This functions supports packages and attributes without depth limitation:
    ``package.package.module.class.class.function.attr`` is valid input.
    However, looking up builtins is not directly supported: use
    ``__builtin__.name``.

    Raises ImportError if importing the module fails or if one requested
    attribute is not found.
    """
    if '.' not in name:
        # shortcut
        __import__(name)
        return sys.modules[name]

    # FIXME clean up this code!
    parts = name.split('.')
    cursor = len(parts)
    module_name = parts[:cursor]
    ret = ''

    while cursor > 0:
        try:
            ret = __import__('.'.join(module_name))
            break
        except ImportError:
            cursor -= 1
            module_name = parts[:cursor]

    if ret == '':
        raise ImportError(parts[0])

    for part in parts[1:]:
        try:
            ret = getattr(ret, part)
        except AttributeError, exc:
            raise ImportError(exc)

    return ret
