import sys
import argparse
import logging
import os
import resource

from circus import logger
from circus.arbiter import Arbiter, ReloadArbiterException
from circus.pidfile import Pidfile
from circus import __version__
from circus.util import MAXFD, REDIRECT_TO, configure_logger, LOG_LEVELS


def get_maxfd():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
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
    # guard to prevent daemonization with gevent loaded
    for module in sys.modules.keys():
        if module.startswith('gevent'):
            raise ValueError('Cannot daemonize if gevent is loaded')

    child_pid = os.fork()

    if child_pid != 0:
        # we're in the parent
        os._exit(0)

    # child process
    os.setsid()

    subchild = os.fork()
    if subchild:
        os._exit(0)

    # subchild
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
    parser.add_argument('--log-level', dest='loglevel',
                        choices=LOG_LEVELS.keys() + [key.upper() for key in
                                                     LOG_LEVELS.keys()],
                        help="log level")
    parser.add_argument('--log-output', dest='logoutput', help=(
        "The location where the logs will be written. The default behavior "
        "is to write to stdout (you can force it by passing '-' to "
        "this option). Takes a filename otherwise."))

    parser.add_argument('--daemon', dest='daemonize', action='store_true',
                        help="Start circusd in the background")
    parser.add_argument('--pidfile', dest='pidfile')
    parser.add_argument('--version', action='store_true', default=False,
                        help='Displays Circus version and exits.')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    if args.config is None:
        parser.print_usage()
        sys.exit(0)

    if args.daemonize:
        daemonize()

    # basic logging configuration
    logging.basicConfig()

    # From here it can also come from the arbiter configuration
    # load the arbiter from config
    arbiter = Arbiter.load_from_config(args.config)

    pidfile = args.pidfile or arbiter.pidfile or None
    if pidfile:
        pidfile = Pidfile(pidfile)

        try:
            pidfile.create(os.getpid())
        except RuntimeError, e:
            print(str(e))
            sys.exit(1)

    # configure the logger
    loglevel = args.loglevel or arbiter.loglevel or 'info'
    logoutput = args.logoutput or arbiter.logoutput or '-'
    configure_logger(logger, loglevel, logoutput)

    try:
        restart_after_stop = True
        while restart_after_stop:
            while True:
                try:
                    arbiter = Arbiter.load_from_config(args.config)
                    arbiter.start()
                    restart_after_stop = False
                except ReloadArbiterException:
                    restart_after_stop = True
                else:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        arbiter._stop()
        if pidfile is not None:
            pidfile.unlink()

    sys.exit(0)


if __name__ == '__main__':
    main()
