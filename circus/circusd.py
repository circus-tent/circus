import sys
import argparse
import ConfigParser
import os
import logging
import resource

from circus import logger
from circus.arbiter import Arbiter
from circus.watcher import Watcher
from circus.pidfile import Pidfile
from circus import util

MAXFD = 1024
if hasattr(os, "devnull"):
    REDIRECT_TO = os.devnull
else:
    REDIRECT_TO = "/dev/null"

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG}

LOG_FMT = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
LOG_DATE_FMT = r"%Y-%m-%d %H:%M:%S"


class DefaultConfigParser(ConfigParser.ConfigParser):
    def dget(self, section, option, default=None, type=str):
        if not self.has_option(section, option):
            return default
        if type is str:
            return self.get(section, option)
        elif type is int:
            return self.getint(section, option)
        elif type is bool:
            return self.getboolean(section, option)
        else:
            raise NotImplementedError()


def get_maxfd():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = MAXFD
    return maxfd


try:
    from os import closerange
except ImportError:
    def closerange(fd_low, fd_high):    # NOQA
        # Iterate through and close all file descriptors.
        for fd in xrange(fd_low, fd_high):
            try:
                os.close(fd)
            except OSError:    # ERROR, fd wasn't open to begin with (ignored)
                pass


def daemonize():
    """\
    Standard daemonization of a process.
    http://www.svbug.com/documentation/comp.unix.programmer-FAQ/faq_2.html#SEC16
    """
    #if not 'CIRCUS_PID' in os.environ:
    if os.fork():
        os._exit(0)
    os.setsid()

    if os.fork():
        os._exit(0)

    os.umask(0)
    maxfd = get_maxfd()
    closerange(0, maxfd)

    os.open(REDIRECT_TO, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)


def main():
    parser = argparse.ArgumentParser(description='Run some shows.')
    parser.add_argument('config', help='configuration file')

    # XXX we should be able to add all these options in the config file as well
    parser.add_argument('--log-level', dest='loglevel', default='info',
            help="log level")
    parser.add_argument('--log-output', dest='logoutput', default='-',
            help="log output")
    parser.add_argument('--daemon', dest='daemonize', action='store_true',
            help="Start circusd in the background")
    parser.add_argument('--pidfile', dest='pidfile')

    args = parser.parse_args()
    cfg = DefaultConfigParser()
    cfg.read(args.config)

    if args.daemonize:
        daemonize()

    pidfile = None
    if args.pidfile:
        pidfile = Pidfile(args.pidfile)

        try:
            pidfile.create(os.getpid())
        except RuntimeError, e:
            print(str(e))
            sys.exit(1)

    # configure the logger
    loglevel = LOG_LEVELS.get(args.loglevel.lower(), logging.INFO)
    logger.setLevel(loglevel)
    if args.logoutput == "-":
        h = logging.StreamHandler()
    else:
        h = logging.FileHandler(args.logoutput)
        util.close_on_exec(h.stream.fileno())
    fmt = logging.Formatter(LOG_FMT, LOG_DATE_FMT)
    h.setFormatter(fmt)
    logger.addHandler(h)

    # Initialize shows to manage
    watchers = []
    for section in cfg.sections():
        if section.startswith("show:"):
            name = section.split("show:", 1)[1]

            cmd = cfg.get(section, 'cmd')
            args = cfg.dget(section, 'args', '')
            if args:
                cmd = "%s %s" % (cmd, args)

            numprocesses = cfg.dget(section, 'numprocesses', 1, int)
            warmup_delay = cfg.dget(section, 'warmup_delay', 0, int)

            working_dir = cfg.dget(section, 'working_dir')
            shell = cfg.dget(section, 'shell', False, bool)
            uid = cfg.dget(section, 'uid')
            gid = cfg.dget(section, 'gid')
            send_hup = cfg.dget(section, 'send_hup', False, bool)
            times = cfg.dget(section, "times", 2, int)
            within = cfg.dget(section, "within", 1, int)
            retry_in = cfg.dget(section, "retry_in", 7, int)
            max_retry = cfg.dget(section, "max_retry", 5, int)
            graceful_timeout = cfg.dget(section, "graceful_timeout", 30, int)

            watcher = Watcher(name, cmd, numprocesses=numprocesses,
                        warmup_delay=warmup_delay, working_dir=working_dir,
                        shell=shell, uid=uid, gid=gid, send_hup=send_hup,
                        times=times, within=within, retry_in=retry_in,
                        max_retry=max_retry, graceful_timeout=graceful_timeout)

            watchers.append(watcher)

    # main circus options
    check = cfg.dget('circus', 'check_delay', 5, int)
    endpoint = cfg.dget('circus', 'endpoint', 'tcp://127.0.0.1:5555')
    pubsub_endpoint = cfg.dget('circus', 'pubsub_endpoint',
            'tcp://127.0.0.1:5556')

    arbiter = Arbiter(watchers, endpoint, pubsub_endpoint, check)
    try:
        arbiter.start()
    finally:
        arbiter.stop()
        if pidfile is not None:
            pidfile.unlink()

    sys.exit(0)

if __name__ == '__main__':
    main()
