import sys
import argparse
import os
import resource

from circus import logger
from circus.arbiter import Arbiter
from circus.pidfile import Pidfile
from circus import __version__
from circus.util import MAXFD, REDIRECT_TO, configure_logger, LOG_LEVELS


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


# http://www.svbug.com/documentation/comp.unix.programmer-FAQ/faq_2.html#SEC16
def daemonize():
    """Standard daemonization of a process.
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
    parser = argparse.ArgumentParser(description='Run some watchers.')
    parser.add_argument('config', help='configuration file', nargs='?')

    # XXX we should be able to add all these options in the config file as well
    parser.add_argument('--log-level', dest='loglevel', default='info',
            choices=LOG_LEVELS.keys() + [key.upper() for key in
                LOG_LEVELS.keys()],
            help="log level")
    parser.add_argument('--log-output', dest='logoutput', default='-',
            help="log output")
    parser.add_argument('--daemon', dest='daemonize', action='store_true',
            help="Start circusd in the background")
    parser.add_argument('--pidfile', dest='pidfile')
    parser.add_argument('--version', action='store_true',
                     default=False, help='Displays Circus version and exits.')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    if args.config is None:
        parser.print_usage()
        sys.exit(0)

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
    configure_logger(logger, args.loglevel, args.logoutput)

    # load the arbiter from config
    arbiter = Arbiter.load_from_config(args.config)
    try:
        arbiter.start()
    except KeyboardInterrupt:
        pass
    finally:
        arbiter.stop()
        if pidfile is not None:
            pidfile.unlink()

    sys.exit(0)


if __name__ == '__main__':
    main()
