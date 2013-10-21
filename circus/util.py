import fcntl
import grp
import logging
import os
import pwd
import re
import shlex
import socket
import sys
import time
import functools
import traceback
from tornado.ioloop import IOLoop
from tornado import gen
from tornado import concurrent
from ConfigParser import (
    ConfigParser, MissingSectionHeaderError, ParsingError, DEFAULTSECT
)
from datetime import timedelta
from functools import wraps

from zmq import ssh


from psutil import AccessDenied, NoSuchProcess, Process

from circus.exc import ConflictError
from circus import logger


# default endpoints
DEFAULT_ENDPOINT_DEALER = "tcp://127.0.0.1:5555"
DEFAULT_ENDPOINT_SUB = "tcp://127.0.0.1:5556"
DEFAULT_ENDPOINT_STATS = "tcp://127.0.0.1:5557"
DEFAULT_ENDPOINT_MULTICAST = "udp://237.219.251.97:12027"


try:
    from setproctitle import setproctitle

    def _setproctitle(title):       # NOQA
        setproctitle(title)
except ImportError:
    def _setproctitle(title):       # NOQA
        return


MAXFD = 1024
if hasattr(os, "devnull"):
    REDIRECT_TO = os.devnull  # PRAGMA: NOCOVER
else:
    REDIRECT_TO = "/dev/null"  # PRAGMA: NOCOVER

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG}

LOG_FMT = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
LOG_DATE_FMT = r"%Y-%m-%d %H:%M:%S"
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
    if not isinstance(n, (int, long)):
        raise TypeError(n)

    prefix = {}
    for i, s in enumerate(_SYMBOLS):
        prefix[s] = 1 << (i + 1) * 10

    for s in reversed(_SYMBOLS):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n


# XXX weak dict ?
_PROCS = {}


def get_info(process=None, interval=0, with_childs=False):
    """Return information about a process. (can be an pid or a Process object)

    If process is None, will return the information about the current process.
    """
    if process is None or isinstance(process, int):
        if process is None:
            pid = os.getpid()
        else:
            pid = process

        if pid in _PROCS:
            process = _PROCS[pid]
        else:
            _PROCS[pid] = process = Process(pid)

    info = {}
    try:
        mem_info = process.get_memory_info()
        info['mem_info1'] = bytes2human(mem_info[0])
        info['mem_info2'] = bytes2human(mem_info[1])
    except AccessDenied:
        info['mem_info1'] = info['mem_info2'] = "N/A"

    try:
        info['cpu'] = process.get_cpu_percent(interval=interval)
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
        try:
            info['nice'] = process.get_nice()
        except AttributeError:
            info['nice'] = process.nice
    except AccessDenied:
        info['nice'] = 'N/A'
    except NoSuchProcess:
        info['nice'] = 'Zombie'

    try:
        cmdline = os.path.basename(shlex.split(process.cmdline[0])[0])
    except (AccessDenied, IndexError):
        cmdline = "N/A"

    try:
        info['create_time'] = process.create_time
    except AccessDenied:
        info['create_time'] = 'N/A'

    try:
        info['age'] = time.time() - process.create_time
    except AccessDenied:
        info['age'] = 'N/A'

    info['cmdline'] = cmdline

    info['children'] = []
    if with_childs:
        for child in process.get_children():
            info['children'].append(get_info(child, interval=interval))

    return info


def to_bool(s):
    if isinstance(s, bool):
        return s

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

    from circus.py3compat import string_types  # circular import fix

    if not isinstance(name, string_types):
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
        # getgrid may raises overflow error on mac/os x, fixed in python2.7.5
        # see http://bugs.python.org/issue17531
        except (KeyError, OverflowError):
            raise ValueError("No such group: %r" % name)

    from circus.py3compat import string_types  # circular import fix

    if not isinstance(name, string_types):
        raise TypeError(name)

    try:
        return grp.getgrnam(name).gr_gid
    except KeyError:
        raise ValueError("No such group: %r" % name)


def parse_env_str(env_str):
    env = dict()
    for kvs in env_str.split(','):
        k, v = kvs.split('=')
        env[k.strip()] = v.strip()
    return parse_env_dict(env)


def parse_env_dict(env):
    ret = dict()
    for k, v in env.iteritems():
        v = re.sub(r'\$([A-Z]+[A-Z0-9_]*)', replace_env, v)
        ret[k.strip()] = v.strip()
    return ret


def replace_env(var):
    return os.getenv(var.group(1))


def env_to_str(env):
    if not env:
        return ""
    return ",".join(["%s=%s" % (k, v) for k, v in
                     sorted(env.items(), key=lambda i: i[0])])


def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def get_python_version():
    """Get a 3 element tuple with the python version"""
    return sys.version_info[:3]


INDENTATION_LEVEL = 0


def debuglog(func):
    @wraps(func)
    def _log(self, *args, **kw):
        if os.environ.get('DEBUG') is None:
            return func(self, *args, **kw)

        from circus import logger
        cls = self.__class__.__name__
        global INDENTATION_LEVEL
        logger.debug("    " * INDENTATION_LEVEL +
                     "'%s.%s' starts" % (cls, func.func_name))
        INDENTATION_LEVEL += 1
        try:
            return func(self, *args, **kw)
        finally:
            INDENTATION_LEVEL -= 1
            logger.debug("    " * INDENTATION_LEVEL +
                         "'%s.%s' ends" % (cls, func.func_name))

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


# taken from werkzeug
class ImportStringError(ImportError):

    """Provides information about a failed :func:`import_string` attempt."""

    #: String in dotted notation that failed to be imported.
    import_name = None
    #: Wrapped exception.
    exception = None

    def __init__(self, import_name, exception):
        self.import_name = import_name
        self.exception = exception

        msg = (
            'import_string() failed for %r. Possible reasons are:\n\n'
            '- missing __init__.py in a package;\n'
            '- package or module path not included in sys.path;\n'
            '- duplicated package or module name taking precedence in '
            'sys.path;\n'
            '- missing module, class, function or variable;\n\n'
            'Debugged import:\n\n%s\n\n'
            'Original exception:\n\n%s: %s')

        name = ''
        tracked = []
        for part in import_name.replace(':', '.').split('.'):
            name += (name and '.') + part
            imported = resolve_name(name, silent=True)
            if imported:
                tracked.append((name, getattr(imported, '__file__', None)))
            else:
                track = ['- %r found in %r.' % (n, i) for n, i in tracked]
                track.append('- %r not found.' % name)
                msg = msg % (import_name, '\n'.join(track),
                             exception.__class__.__name__, str(exception))
                break

        ImportError.__init__(self, msg)

    def __repr__(self):
        return '<%s(%r, %r)>' % (self.__class__.__name__, self.import_name,
                                 self.exception)


def resolve_name(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :return: imported object
    """
    # force the import name to automatically convert to strings
    if isinstance(import_name, unicode):
        import_name = str(import_name)
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
        else:
            return __import__(import_name)
            # __import__ is not able to handle unicode strings in the fromlist
        # if the module is a package
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        try:
            return getattr(__import__(module, None, None, [obj]), obj)
        except (ImportError, AttributeError):
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            modname = module + '.' + obj
            __import__(modname)
            return sys.modules[modname]
    except ImportError as e:
        if not silent:
            raise ImportStringError(import_name, e), None, sys.exc_info()[2]


_SECTION_NAME = '\w\.\-'
_PATTERN1 = r'\$\(%%s\.([%s]+)\)' % _SECTION_NAME
_PATTERN2 = r'\(\(%%s\.([%s]+)\)\)' % _SECTION_NAME
_CIRCUS_VAR = re.compile(_PATTERN1 % 'circus' + '|' +
                         _PATTERN2 % 'circus', re.I)


def replace_gnu_args(data, prefix='circus', **options):
    fmt_options = {}
    for key, value in options.items():
        key = key.lower()

        if prefix is not None:
            key = '%s.%s' % (prefix, key)

        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                subkey = subkey.lower()
                subkey = '%s.%s' % (key, subkey)
                fmt_options[subkey] = subvalue
        else:
            fmt_options[key] = value

    if prefix is None:
        pattern = r'\$\(([%s]+)\)|\(\(([%s]+)\)\)' % (_SECTION_NAME,
                                                      _SECTION_NAME)
        match = re.compile(pattern, re.I)
    elif prefix == 'circus':
        match = _CIRCUS_VAR
    else:
        match = re.compile(_PATTERN1 % prefix + '|' + _PATTERN2 % prefix,
                           re.I)

    def _repl(matchobj):
        option = None

        for result in matchobj.groups():
            if result is not None:
                option = result.lower()
                break

        if prefix is not None and not option.startswith(prefix):
            option = '%s.%s' % (prefix, option)

        if option in fmt_options:
            return str(fmt_options[option])

        return matchobj.group()

    return match.sub(_repl, data)


class ObjectDict(dict):

    def __getattr__(self, item):
        return self[item]


def configure_logger(logger, level='INFO', output="-"):
    loglevel = LOG_LEVELS.get(level.lower(), logging.INFO)
    logger.setLevel(loglevel)
    if output == "-":
        h = logging.StreamHandler()
    else:
        h = logging.FileHandler(output)
        close_on_exec(h.stream.fileno())
    fmt = logging.Formatter(LOG_FMT, LOG_DATE_FMT)
    h.setFormatter(fmt)
    logger.handlers = [h]


class StrictConfigParser(ConfigParser):

    def _read(self, fp, fpname):
        cursect = None                        # None, or a dictionary
        optname = None
        lineno = 0
        e = None                              # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname].append(value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        # we're extending/overriding, we're good
                        cursect = self._sections[sectname]
                    elif sectname == DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        cursect['__name__'] = sectname
                        self._sections[sectname] = cursect
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    try:
                        mo = self._optcre.match(line)   # 2.7
                    except AttributeError:
                        mo = self.OPTCRE.match(line)    # 2.6
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        optname = self.optionxform(optname.rstrip())
                        # We don't want to override.
                        if optname in cursect:
                            continue
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            if vi in ('=', ':') and ';' in optval:
                                # ';' is a comment delimiter only if it follows
                                # a spacing character
                                pos = optval.find(';')
                                if pos != -1 and optval[pos - 1].isspace():
                                    optval = optval[:pos]
                            optval = optval.strip()
                            # allow empty values
                            if optval == '""':
                                optval = ''
                            cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

        # join the multi-line values collected while reading
        all_sections = [self._defaults]
        all_sections.extend(self._sections.values())
        for options in all_sections:
            for name, val in options.items():
                if isinstance(val, list):
                    options[name] = '\n'.join(val)


def get_connection(socket, endpoint, ssh_server=None, ssh_keyfile=None):
    if ssh_server is None:
        socket.connect(endpoint)
    else:
        try:
            try:
                ssh.tunnel_connection(socket, endpoint, ssh_server,
                                      keyfile=ssh_keyfile)
            except ImportError:
                ssh.tunnel_connection(socket, endpoint, ssh_server,
                                      keyfile=ssh_keyfile, paramiko=True)
        except ImportError:
            raise ImportError("pexpect was not found, and failed to use "
                              "Paramiko.  You need to install Paramiko")


def load_virtualenv(watcher):
    if not watcher.copy_env:
        raise ValueError('copy_env must be True to to use virtualenv')

    py_ver = sys.version.split()[0][:3]

    # XXX Posix scheme - need to add others
    sitedir = os.path.join(watcher.virtualenv, 'lib', 'python' + py_ver,
                           'site-packages')

    if not os.path.exists(sitedir):
        raise ValueError("%s does not exist" % sitedir)

    def process_pth(sitedir, name):
        packages = set()
        fullname = os.path.join(sitedir, name)
        try:
            f = open(fullname, "rU")
        except IOError:
            return
        with f:
            for line in f.readlines():
                if line.startswith(("#", "import")):
                    continue
                line = line.rstrip()
                pkg_path = os.path.abspath(os.path.join(sitedir, line))
                if os.path.exists(pkg_path):
                    packages.add(pkg_path)
        return packages

    venv_pkgs = set()
    dotpth = os.extsep + "pth"
    for name in os.listdir(sitedir):
        if name.endswith(dotpth):
            try:
                packages = process_pth(sitedir, name)
                if packages:
                    venv_pkgs |= packages
            except OSError:
                continue

    py_path = watcher.env.get('PYTHONPATH')
    path = None

    if venv_pkgs:
        venv_path = os.pathsep.join(venv_pkgs)

        if py_path:
            path = os.pathsep.join([venv_path, py_path])
        else:
            path = venv_path

    # Add watcher virtualenv site-packages dir to the python path
    if path and not sitedir in path.split(os.pathsep):
        path = os.pathsep.join([path, sitedir])
    else:
        if py_path:
            path = os.pathsep.join([py_path, sitedir])
        else:
            path = sitedir

    watcher.env['PYTHONPATH'] = path


def create_udp_socket(mcast_addr, mcast_port):
    """Create an udp multicast socket for circusd cluster auto-discovery.
    mcast_addr must be between 224.0.0.0 and 239.255.255.255
    """
    try:
        ip_splitted = map(int, mcast_addr.split('.'))
        mcast_port = int(mcast_port)
    except ValueError:
        raise ValueError('Wrong UDP multicast_endpoint configuration. Should '
                         'looks like: "%r"' % DEFAULT_ENDPOINT_MULTICAST)

    if ip_splitted[0] < 224 or ip_splitted[0] > 239:
        raise ValueError('The multicast address is not valid should be '
                         'between 224.0.0.0 and 239.255.255.255')

    any_addr = "0.0.0.0"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Allow reutilization of addr
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Some platform exposes SO_REUSEPORT
    if hasattr(socket, 'SO_REUSEPORT'):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    # Put packet ttl to max
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    # Register socket to multicast group
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(mcast_addr) + socket.inet_aton(any_addr))
    # And finally bind all interfaces
    sock.bind((any_addr, mcast_port))
    return sock


# taken from http://stackoverflow.com/questions/1165352

class DictDiffer(object):

    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """

    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = (set(current_dict.keys()),
                                           set(past_dict.keys()))
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] == self.current_dict[o])


def dict_differ(dict1, dict2):
    return len(DictDiffer(dict1, dict2).changed()) > 0


def _synchronized_cb(arbiter, future):
    if arbiter is not None:
        arbiter._exclusive_running_command = None


def synchronized(name):
    def real_decorator(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            arbiter = None
            if hasattr(self, "arbiter"):
                arbiter = self.arbiter
            elif hasattr(self, "_exclusive_running_command"):
                arbiter = self
            if arbiter is not None:
                if arbiter._exclusive_running_command is not None:
                    raise ConflictError("arbiter is already running %s command"
                                        % arbiter._exclusive_running_command)
                arbiter._exclusive_running_command = name
            resp = None
            try:
                resp = f(self, *args, **kwargs)
            finally:
                if isinstance(resp, concurrent.Future):
                    cb = functools.partial(_synchronized_cb, arbiter)
                    resp.add_done_callback(cb)
                else:
                    if arbiter is not None:
                        arbiter._exclusive_running_command = None
            return resp
        return wrapper
    return real_decorator


def tornado_sleep(duration):
    """Sleep without blocking the tornado event loop

    To use with a gen.coroutines decorated function
    Thanks to http://stackoverflow.com/a/11135204/433050
    """
    return gen.Task(IOLoop.instance().add_timeout, time.time() + duration)


class TransformableFuture(concurrent.Future):

    _upstream_future = None
    _upstream_callback = None
    _transform_function = lambda x: x
    _result = None
    _exception = None

    def set_transform_function(self, fn):
        self._transform_function = fn

    def set_upstream_future(self, upstream_future):
        self._upstream_future = upstream_future

    def result(self, timeout=None):
        if self._upstream_future is None:
            raise Exception("upstream_future is not set")
        return self._transform_function(self._result)

    def _internal_callback(self, future):
        self._result = future.result()
        self._exception = future.exception()
        if self._upstream_callback is not None:
            self._upstream_callback(self)

    def add_done_callback(self, fn):
        if self._upstream_future is None:
            raise Exception("upstream_future is not set")
        self._upstream_callback = fn
        self._upstream_future.add_done_callback(self._internal_callback)

    def exception(self, timeout=None):
        if self._exception:
            return self._exception
        else:
            return None


def check_future_exception_and_log(future):
    if isinstance(future, concurrent.Future):
        exception = future.exception()
        if exception is not None:
            logger.error("exception %s caught" % exception)
            if hasattr(future, "exc_info"):
                exc_info = future.exc_info()
                traceback.print_tb(exc_info[2])
            return exception
