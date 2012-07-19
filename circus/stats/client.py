import argparse
import sys
import json
import curses
from collections import defaultdict
import errno
import threading
import time

import zmq

from circus.consumer import CircusConsumer
from circus import __version__
from circus.util import DEFAULT_ENDPOINT_STATS


class StatsClient(CircusConsumer):
    def __init__(self, endpoint=DEFAULT_ENDPOINT_STATS, ssh_server=None,
                 context=None):
        CircusConsumer.__init__(self, ['stat.'], context, endpoint, ssh_server)

    def iter_messages(self):
        """ Yields tuples of (watcher, subtopic, stat)"""
        recv = self.pubsub_socket.recv_multipart

        with self:
            while True:
                try:
                    events = dict(self.poller.poll(self.timeout * 1000))
                except zmq.ZMQError as e:
                    if e.errno == errno.EINTR:
                        continue

                if len(events) == 0:
                    print 'nothing'
                    continue

                try:
                    topic, stat = recv()
                except zmq.core.error.ZMQError, e:
                    if e.errno != errno.EINTR:
                        raise
                    else:
                        sys.exc_clear()
                        continue

                topic = topic.split('.')
                if len(topic) == 3:
                    __, watcher, subtopic = topic
                    yield watcher, subtopic, json.loads(stat)
                elif len(topic) == 2:
                    __, watcher = topic
                    yield watcher, None, json.loads(stat)


def _paint(stdscr, watchers=None, old_h=None, old_w=None):

    def addstr(line, *args):
        if line < current_h:
            stdscr.addstr(line, *args)

    current_h, current_w = stdscr.getmaxyx()

    if watchers is None:
        stdscr.erase()
        addstr(1, 0, '*** Waiting for data ***')
        stdscr.refresh()
        return current_h, current_w

    if current_h != old_h or current_w != old_w:
        # we need a resize
        curses.endwin()
        stdscr.refresh()
        stdscr.erase()
        stdscr.resize(current_h, current_w)

    addstr(0, 0, 'Circus Top')
    addstr(1, 0, '-' * current_w)
    names = watchers.keys()
    names.sort()
    line = 2
    for name in names:
        if name in ('circusd-stats', 'circushttpd'):
            continue

        stdscr.addstr(line, 0, name.replace('-', '.'))
        line += 1

        if name == 'sockets':
            addstr(line, 3, 'ADDRESS')
            addstr(line, 28, 'HITS')

            line += 1

            fds = []

            for __, stats in watchers[name].items():
                if 'addresses' in stats:
                    total = stats['reads']
                    continue

                reads = stats['reads']
                address = stats['address']
                fds.append((reads, address))

            fds.sort()
            fds.reverse()

            for reads, address in fds:
                addstr(line, 2, str(address))
                addstr(line, 29, '%3d' % reads)
                line += 1

            addstr(line, 29, '%3d (sum)' % total)
            line += 2

        else:
            addstr(line, 3, 'PID')
            addstr(line, 28, 'CPU (%)')
            addstr(line, 48, 'MEMORY (%)')
            addstr(line, 68, 'AGE (s)')
            line += 1

            # sorting by CPU
            pids = []
            total = '', 'N/A', 'N/A', None
            for pid, stat in watchers[name].items():
                if stat['cpu'] == 'N/A':
                    cpu = 'N/A'
                else:
                    cpu = "%.2f" % stat['cpu']

                if stat['mem'] == 'N/A':
                    mem = 'N/A'
                else:
                    mem = "%.2f" % stat['mem']

                if stat['age'] == 'N/A':
                    age = 'N/A'
                else:
                    age = "%.2f" % stat['age']

                if pid == 'all' or isinstance(pid, list):
                    total = (cpu + ' (avg)', mem + ' (sum)', age + ' (older)',
                             '', None)
                else:
                    pids.append((cpu, mem, age, str(stat['pid']),
                                 stat['name']))

            pids.sort()
            pids.reverse()
            pids = pids[:10] + [total]

            for cpu, mem, age, pid, name in pids:
                if name is not None:
                    pid = '%s (%s)' % (pid, name)
                addstr(line, 2, pid)
                addstr(line, 29, cpu)
                addstr(line, 49, mem)
                addstr(line, 69, age)
                line += 1
            line += 1

    if line <= current_h and len(watchers) > 0:
        stdscr.addstr(line, 0, '-' * current_w)
    stdscr.refresh()
    return current_h, current_w


class Painter(threading.Thread):
    def __init__(self, screen, watchers, h, w):
        threading.Thread.__init__(self)
        self.daemon = True
        self.screen = screen
        self.watchers = watchers
        self.running = False
        self.h = h
        self.w = w

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.h, self.w = _paint(self.screen, self.watchers, self.h, self.w)
            time.sleep(1.)


def main():
    desc = 'Runs Circus Top'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--endpoint',
            help='The circusd-stats ZeroMQ socket to connect to',
            default=DEFAULT_ENDPOINT_STATS)

    parser.add_argument('--version', action='store_true',
                     default=False, help='Displays Circus version and exits.')

    parser.add_argument('--ssh', default=None, help='SSH Server')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    stdscr = curses.initscr()
    watchers = defaultdict(dict)
    h, w = _paint(stdscr)
    time.sleep(1.)

    painter = Painter(stdscr, watchers, h, w)
    painter.start()

    try:
        client = StatsClient(args.endpoint, args.ssh)
        try:
            for watcher, subtopic, stat in client:
                # building the line
                stat['watcher'] = watcher
                if subtopic is None:
                    subtopic = 'all'

                # adding it to the structure
                watchers[watcher][subtopic] = stat
        except KeyboardInterrupt:
            client.stop()
    finally:
        painter.stop()
        curses.endwin()


if __name__ == '__main__':
    main()
