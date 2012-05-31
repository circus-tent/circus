import argparse
import sys
import json
import curses
from collections import defaultdict
import errno

import zmq

from circus.consumer import CircusConsumer
from circus import __version__


class StatsClient(CircusConsumer):
    def __init__(self, endpoint='tcp://127.0.0.1:5557', context=None):
        CircusConsumer.__init__(self, ['stat.'], context, endpoint)

    def iter_messages(self):
        """ Yields tuples of (watcher, pid, stat)"""
        with self:
            while True:
                try:
                    topic, stat = self.pubsub_socket.recv_multipart()
                except zmq.core.error.ZMQError, e:
                    if e.errno != errno.EINTR:
                        raise
                    else:
                        sys.exc_clear()
                        continue

                topic = topic.split('.')
                if len(topic) == 3:
                    __, watcher, pid = topic
                    yield watcher, long(pid), json.loads(stat)
                else:
                    __, watcher = topic
                    yield watcher, None, json.loads(stat)


def _paint(stdscr, watchers):
    stdscr.erase()
    names = watchers.keys()
    names.sort()
    stdscr.addstr(0, 0, 'Circus Top')
    stdscr.addstr(1, 0, '-' * 100)
    line = 2
    for name in names:
        if name == 'circusd-stats':
            continue
        stdscr.addstr(line, 0, name)
        line += 1
        stdscr.addstr(line, 3, 'PID')
        stdscr.addstr(line, 28, 'CPU (%)')
        stdscr.addstr(line, 48, 'MEMORY (%)')

        line += 1

        # sorting by CPU
        pids = []
        total = '', 'N/A', 'N/A', None
        for pid, stat in watchers[name].items():
            if pid == 'all' or isinstance(pid, list):

                total = ("%.2f" % stat['cpu'] + ' (avg)',
                         "%.2f" % stat['mem'] + ' (sum)', '', None)
            else:
                pids.append(("%.2f" % stat['cpu'], "%.2f" % stat['mem'],
                             str(stat['pid']), stat['name']))

        pids.sort()
        pids.reverse()
        pids = pids[:10] + [total]

        for cpu, mem, pid, name in pids:
            if name is not None:
                pid = '%s (%s)' % (pid, name)
            stdscr.addstr(line, 2, pid)
            stdscr.addstr(line, 29, cpu)
            stdscr.addstr(line, 49, mem)
            line += 1
        line += 1

    stdscr.addstr(line, 0, '-' * 100)
    stdscr.refresh()


def main():
    desc = 'Runs Circus Top'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--endpoint',
            help='The circusd-stats ZeroMQ socket to connect to',
            default='tcp://127.0.0.1:5557')

    parser.add_argument('--version', action='store_true',
                     default=False, help='Displays Circus version and exits.')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    stdscr = curses.initscr()
    watchers = defaultdict(dict)

    try:
        client = StatsClient(args.endpoint)
        try:
            for watcher, pid, stat in client:
                # building the line
                stat['watcher'] = watcher
                if pid is None:
                    pid = 'all'

                # adding it to the structure
                watchers[watcher][pid] = stat

                # now painting
                _paint(stdscr, watchers)

        except KeyboardInterrupt:
            client.stop()
    finally:
        curses.endwin()


if __name__ == '__main__':
    main()
