
"""
Stats architecture:

 * streamer.StatsStreamer listens to circusd events and maintain a list of pids
 * collector.StatsCollector runs a pool of threads that compute stats for each
   pid in the list. Each stat is pushed in a queue
 * publisher.StatsPublisher continuously pushes those stats in a zmq PUB socket
 * client.StatsClient is a simple subscriber that can be used to intercept the
   stream of stats.
"""
import sys
import signal
import argparse

from circus.stats.streamer import StatsStreamer
from circus.util import configure_logger
from circus.sighandler import SysHandler
from circus import logger
from circus import util
from circus import __version__


def main():
    desc = 'Runs the stats aggregator for Circus'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--endpoint',
                        help='The circusd ZeroMQ socket to connect to',
                        default=util.DEFAULT_ENDPOINT_DEALER)

    parser.add_argument('--pubsub',
                        help='The circusd ZeroMQ pub/sub socket to connect to',
                        default=util.DEFAULT_ENDPOINT_SUB)

    parser.add_argument('--statspoint',
                        help='The ZeroMQ pub/sub socket to send data to',
                        default=util.DEFAULT_ENDPOINT_STATS)

    parser.add_argument('--log-level', dest='loglevel', default='info',
                        help="log level")

    parser.add_argument('--log-output', dest='logoutput', default='-',
                        help="log output")

    parser.add_argument('--version', action='store_true',
                        default=False,
                        help='Displays Circus version and exits.')

    parser.add_argument('--ssh', default=None, help='SSH Server')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    # configure the logger
    configure_logger(logger, args.loglevel, args.logoutput)

    stats = StatsStreamer(args.endpoint, args.pubsub, args.statspoint,
                          args.ssh)

    # Register some sighandlers to stop the loop when killed
    for sig in SysHandler.SIGNALS:
        signal.signal(
            sig, lambda *_: stats.loop.add_callback_from_signal(stats.stop)
        )

    try:
        stats.start()
    finally:
        stats.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
