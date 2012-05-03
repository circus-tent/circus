import sys
import argparse

from circus.stats.streamer import StatsStreamer


def main():
    desc = 'Runs the stats aggregator for Circus'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--endpoint',
            help='The ZeroMQ pub/sub socket to connect to',
            default='tcp://127.0.0.1:5555')

    parser.add_argument('--pubsub',
            help='The ZeroMQ pub/sub socket to connect to',
            default='tcp://127.0.0.1:5556')

    args = parser.parse_args()
    stats = StatsStreamer(args.endpoint, args.pubsub)

    try:
        stats.start()
    finally:
        stats.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
