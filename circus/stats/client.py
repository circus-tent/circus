from circus.consumer import CircusConsumer
import json
import curses
from collections import defaultdict


class StatsClient(CircusConsumer):
    def __init__(self, endpoint='tcp://127.0.0.1:5557', context=None):
        CircusConsumer.__init__(self, ['stat.'], context, endpoint)

    def iter_messages(self):
        """ Yields tuples of (watcher, pid, stat)"""
        with self:
            while True:
                topic, stat = self.pubsub_socket.recv_multipart()
                topic = topic.split('.')
                if len(topic) == 3:
                    __, watcher, pid = topic
                    yield watcher, long(pid), json.loads(stat)
                else:
                    __, watcher = topic
                    yield watcher, None, json.loads(stat)


if __name__ == '__main__':
    stdscr = curses.initscr()
    watchers = defaultdict(dict)

    def paint(watchers):
        stdscr.erase()
        names = watchers.keys()
        names.sort()
        stdscr.addstr(0, 0, 'Circus Top')
        stdscr.addstr(1, 0, '-' * 100)
        line = 2
        for name in names:
            stdscr.addstr(line, 0, name)
            line += 1
            pids = watchers[name].keys()
            pids.sort()
            for pid in pids:
                pid = watchers[name][pid]['pid']
                if pid == 'all':
                    spid = 'Total  '
                elif isinstance(pid, list):
                    spid = 'Total  '
                    pid = 'all'
                else:
                    spid = str(pid)
                cpu = str(watchers[name][pid]['cpu']) + '%'
                stdscr.addstr(line, 2, spid)
                stdscr.addstr(line, 25, cpu)
                line += 1
            line += 1

        stdscr.addstr(line, 0, '-' * 100)
        stdscr.refresh()

    try:
        client = StatsClient()
        try:
            for watcher, pid, stat in client:
                # building the line
                stat['watcher'] = watcher
                if pid is None:
                    pid = 'all'


                # adding it to the structure
                watchers[watcher][pid] = stat

                # now painting
                paint(watchers)

        except KeyboardInterrupt:
            client.stop()
    finally:
        curses.endwin()
