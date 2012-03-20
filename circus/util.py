from datetime import timedelta
import grp
import os
import pwd
import fcntl
from functools import wraps

from psutil.error import AccessDenied, NoSuchProcess
from circus import logger


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
        cmdline = os.path.basename(process.cmdline[0])
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
        except KeyError:
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
        except KeyError:
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
