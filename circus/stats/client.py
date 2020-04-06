import argparse
import sys
import curses
from collections import defaultdict
import errno
import circus.fixed_threading as threading
import time
import logging

import zmq
import zmq.utils.jsonapi as json

from circus.consumer import CircusConsumer
from circus import __version__
from circus.util import DEFAULT_ENDPOINT_STATS, to_str


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
                    raise

                if len(events) == 0:
                    continue

                try:
                    topic, stat = recv()
                except zmq.core.error.ZMQError as e:
                    if e.errno != errno.EINTR:
                        raise
                    else:
                        try:
                            sys.exc_clear()
                        except Exception:
                            pass
                        continue

                topic = to_str(topic).split('.')
                if len(topic) == 3:
                    __, watcher, subtopic = topic
                    yield watcher, subtopic, json.loads(stat)
                elif len(topic) == 2:
                    __, watcher = topic
                    yield watcher, None, json.loads(stat)


def _paint(stdscr, watchers=None, old_h=None, old_w=None):

    current_h, current_w = stdscr.getmaxyx()

    def addstr(x, y, text):
        text_len = len(text)

        if x < current_h:
            padding = current_w - y
            if text_len >= padding:
                text = text[:padding - 1]
            else:
                text += ' ' * (padding - text_len - 1)

            if text == '':
                return

            stdscr.addstr(x, y, text)

    stdscr.erase()

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
    names = sorted(watchers.keys())
    line = 2
    for name in names:
        if name in ('circusd-stats', 'circushttpd'):
            continue

        addstr(line, 0, name.replace('-', '.'))
        line += 1

        if name == 'sockets':
            addstr(line, 3, 'ADDRESS')
            addstr(line, 28, 'HITS')

            line += 1

            fds = []

            total = 0
            for stats in watchers[name].values():
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

    if line < current_h and len(watchers) > 0:
        addstr(line, 0, '-' * current_w)

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
    logging.basicConfig()
    desc = 'Runs Circus Top'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--endpoint',
                        help='The circusd-stats ZeroMQ socket to connect to',
                        default=DEFAULT_ENDPOINT_STATS)

    parser.add_argument('--version', action='store_true',
                        default=False,
                        help='Displays Circus version and exits.')

    parser.add_argument('--ssh', default=None, help='SSH Server')

    parser.add_argument('--process-timeout',
                        default=3,
                        help='After this delay of inactivity, a process will \
                         be removed')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    stdscr = curses.initscr()
    watchers = defaultdict(dict)
    h, w = _paint(stdscr)
    last_refresh_for_pid = defaultdict(float)
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

                # Clean pids that have not been updated recently
                for pid in tuple(p for p in watchers[watcher] if p.isdigit()):
                    if (last_refresh_for_pid[pid] <
                            time.time() - int(args.process_timeout)):
                        del watchers[watcher][pid]
                last_refresh_for_pid[subtopic] = time.time()

                # adding it to the structure
                watchers[watcher][subtopic] = stat
        except KeyboardInterrupt:
            client.stop()
    finally:
        painter.stop()
        curses.endwin()


if __name__ == '__main__':
    main()
