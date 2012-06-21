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


class StatsClient(CircusConsumer):
    def __init__(self, endpoint='tcp://127.0.0.1:5557', context=None):
        CircusConsumer.__init__(self, ['stat.'], context, endpoint)

    def iter_messages(self):
        """ Yields tuples of (watcher, pid, stat)"""
        recv = self.pubsub_socket.recv_multipart

        with self:
            while True:
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
                    __, watcher, pid = topic
                    yield watcher, long(pid), json.loads(stat)
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
        if name == 'circusd-stats':
            continue

        stdscr.addstr(line, 0, name.replace('-', '.'))
        line += 1

        if name == 'sockets':
            addstr(line, 3, 'ADDRESS')
            addstr(line, 28, 'READS / S')
            addstr(line, 48, 'WRITES / S')
            addstr(line, 68, 'ERRORS / S')

            line += 1

            total = '', 'N/A', 'N/A', None
            fds = []

            for __, stats in watchers[name].items():
                fd = stats['fd']
                reads = stats['reads']
                writes = stats['writes']
                errors = stats['errors']
                address = stats['address']
                fds.append((reads, writes, errors, fds, address))

            fds.sort()
            fds.reverse()

            for reads, writes, errors, fd, address in fds:
                addstr(line, 2, str(address))
                addstr(line, 29, str(reads))
                addstr(line, 49, str(writes))
                addstr(line, 69, str(errors))
                line += 1

            line += 1

        else:
            addstr(line, 3, 'PID')
            addstr(line, 28, 'CPU (%)')
            addstr(line, 48, 'MEMORY (%)')
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

                if pid == 'all' or isinstance(pid, list):
                    total = (cpu + ' (avg)', mem + ' (sum)', '', None)
                else:
                    pids.append((cpu, mem, str(stat['pid']), stat['name']))

            pids.sort()
            pids.reverse()
            pids = pids[:10] + [total]

            for cpu, mem, pid, name in pids:
                if name is not None:
                    pid = '%s (%s)' % (pid, name)
                addstr(line, 2, pid)
                addstr(line, 29, cpu)
                addstr(line, 49, mem)
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
            default='tcp://127.0.0.1:5557')

    parser.add_argument('--version', action='store_true',
                     default=False, help='Displays Circus version and exits.')

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
        client = StatsClient(args.endpoint)
        try:
            for watcher, pid, stat in client:
                # building the line
                stat['watcher'] = watcher
                if pid is None:
                    pid = 'all'

                # adding it to the structure
                watchers[watcher][pid] = stat
        except KeyboardInterrupt:
            client.stop()
    finally:
        painter.stop()
        curses.endwin()


if __name__ == '__main__':
    main()
