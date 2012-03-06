from datetime import timedelta
import grp
import os
import pwd

from psutil.error import AccessDenied

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
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    if not isinstance(n, int):
        return n

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

    for name in ('pid', 'username', 'nice'):
        try:
            info[name] = getattr(process, name)
        except AccessDenied:
            info[name] = 'N/A'


    try:
        cmdline = os.path.basename(process.cmdline[0])
    except AccessDenied:
        cmdline = "N/A"

    info['cmdline'] = cmdline

    return info


def to_bool(s):
    if s.lower().strip() in ("true", "1",):
        return True
    elif s.lower().strip() in ("false", "0"):
        return False
    else:
        raise ValueError("%r isn't not a boolean" % s)

def to_uid(val):
    if val is None:
        return val

    elif isinstance(val, int):
        return val
    elif val.isdigit():
        return int(val)
    else:
        try:
            return pwd.getpwnam(val).pw_uid
        except KeyError:
            raise ValueError("%r isn't a valid uid")

def to_gid(val):
    if val is None:
        return val
    elif isinstance(val, int):
        return val
    elif val.isdigit():
        return int(val)
    else:
        try:
            return grp.getgrnam(val).gr_gid
        except KeyError:
            raise ConfigError("No such group: '%s'" % val)

def parse_env(env_str):
    env = {}
    for kvs in env_str.split(","):
        k, v = kvs.split("=")
        env[k.strip()] = v.strip()
    return env

def env_to_str(env):
    if not env:
        return ""
    return ",".join(["%s=%s" % (k,v) for k, v in env.items()])


def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)
