import sys
import argparse
import os
try:
    import resource
except ImportError:
    resource = None     # NOQA

from circus import logger
from circus.arbiter import Arbiter
from circus.pidfile import Pidfile
from circus import __version__
from circus.util import MAXFD, REDIRECT_TO, configure_logger, LOG_LEVELS
from circus.util import check_future_exception_and_log


def get_maxfd():
    if not resource:
        maxfd = MAXFD
    else:
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd == resource.RLIM_INFINITY:
            maxfd = MAXFD
    return maxfd


try:
    from os import closerange
except ImportError:
    def closerange(fd_low, fd_high):    # NOQA
        # Iterate through and close all file descriptors.
        for fd in range(fd_low, fd_high):
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

    if hasattr(os, 'fork'):
        child_pid = os.fork()
    else:
        raise ValueError("Daemonizing is not available on this platform.")

    if child_pid != 0:
        # we're in the parent
        os._exit(0)

    # child process
    os.setsid()

    subchild = os.fork()
    if subchild:
        os._exit(0)

    # subchild
    maxfd = get_maxfd()
    closerange(0, maxfd)

    os.open(REDIRECT_TO, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)


def main():
    import zmq
    try:
        zmq_version = [int(part) for part in zmq.__version__.split('.')[:2]]
        if len(zmq_version) < 2:
            raise ValueError()
    except (AttributeError, ValueError):
        print('Unknown PyZQM version - aborting...')
        sys.exit(0)

    if zmq_version[0] < 13 or (zmq_version[0] == 13 and zmq_version[1] < 1):
        print('circusd needs PyZMQ >= 13.1.0 to run - aborting...')
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Run some watchers.')
    parser.add_argument('config', help='configuration file', nargs='?')

    # XXX we should be able to add all these options in the config file as well
    parser.add_argument('--log-level', dest='loglevel',
                        choices=list(LOG_LEVELS.keys()) + [
                            key.upper() for key in LOG_LEVELS.keys()],
                        help="log level")
    parser.add_argument('--log-output', dest='logoutput', help=(
        "The location where the logs will be written. The default behavior "
        "is to write to stdout (you can force it by passing '-' to "
        "this option). Takes a filename otherwise."))
    parser.add_argument("--logger-config", dest="loggerconfig", help=(
        "The location where a standard Python logger configuration INI, "
        "JSON or YAML file can be found.  This can be used to override "
        "the default logging configuration for the arbiter."))

    parser.add_argument('--daemon', dest='daemonize', action='store_true',
                        help="Start circusd in the background. Not supported "
                             "on Windows")
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

    # From here it can also come from the arbiter configuration
    # load the arbiter from config
    arbiter = Arbiter.load_from_config(args.config)

    # go ahead and set umask early if it is in the config
    if arbiter.umask is not None:
        os.umask(arbiter.umask)

    pidfile = args.pidfile or arbiter.pidfile or None
    if pidfile:
        pidfile = Pidfile(pidfile)

        try:
            pidfile.create(os.getpid())
        except RuntimeError as e:
            print(str(e))
            sys.exit(1)

    # configure the logger
    loglevel = args.loglevel or arbiter.loglevel or 'info'
    logoutput = args.logoutput or arbiter.logoutput or '-'
    loggerconfig = args.loggerconfig or arbiter.loggerconfig or None
    configure_logger(logger, loglevel, logoutput, loggerconfig)

    # Main loop
    restart = True
    while restart:
        try:
            arbiter = arbiter or Arbiter.load_from_config(args.config)
            future = arbiter.start()
            restart = False
            if check_future_exception_and_log(future) is None:
                restart = arbiter._restarting
        except Exception as e:
            # emergency stop
            arbiter.loop.run_sync(arbiter._emergency_stop)
            raise(e)
        except KeyboardInterrupt:
            pass
        finally:
            arbiter = None
            # Do not delete pid file if not going to exit
            if pidfile is not None and restart is False:
                pidfile.unlink()

    sys.exit(0)


if __name__ == '__main__':
    main()
