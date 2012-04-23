import os
from collections import defaultdict
from threading import Thread
import time
from circus.commands import get_commands
from circus.client import CircusClient, CallError


_DIR = os.path.dirname(__file__)
client = None
cmds = get_commands()
MAX_STATS = 100


class Refresher(Thread):
    def __init__(self, client):
        Thread.__init__(self)
        self.client = client
        self.daemon = True
        self.running = False
        self.cclient = CircusClient(endpoint=client.endpoint)

    def run(self):
        stats = self.client.stats
        call = self.cclient.call
        self.running = True
        while self.running:
            for name, __ in self.client.watchers:
                msg = cmds['stats'].make_message(name=name)
                res = call(msg)
                stats[name].insert(0, res['info'])
                if len(stats[name]) > MAX_STATS:
                    stats[name][:] = stats[name][:MAX_STATS]

            time.sleep(.2)


class LiveClient(object):
    def __init__(self, endpoint):
        self.endpoint = str(endpoint)
        self.client = CircusClient(endpoint=self.endpoint)
        self.connected = False
        self.watchers = []
        self.stats = defaultdict(list)
        self.refresher = Refresher(self)

    def stop(self):
        self.client.stop()
        self.refresher.running = False
        self.refresher.join()

    def verify(self):
        self.watchers = []
        # trying to list the watchers
        msg = cmds['list'].make_message()
        try:
            res = self.client.call(msg)
            self.connected = True
            for watcher in res['watchers']:
                msg = cmds['options'].make_message(name=watcher)
                options = self.client.call(msg)
                self.watchers.append((watcher, options['options']))
            self.watchers.sort()
            if not self.refresher.running:
                self.refresher.start()
        except CallError:
            self.connected = False

    def killproc(self, name, pid):
        msg = cmds['killproc'].make_message(name=name, pid=pid)
        res = self.client.call(msg)
        self.verify()  # will do better later
        return res['numprocesses']

    def get_option(self, name, option):
        watchers = dict(self.watchers)
        return watchers[name][option]

    def get_options(self, name):
        watchers = dict(self.watchers)
        return watchers[name].items()

    def incrproc(self, name):
        msg = cmds['incr'].make_message(name=name)
        res = self.client.call(msg)
        self.verify()  # will do better later
        return res['numprocesses']

    def decrproc(self, name):
        msg = cmds['decr'].make_message(name=name)
        res = self.client.call(msg)
        self.verify()  # will do better later
        return res['numprocesses']

    def get_stats(self, name):
        return self.stats[name]

    def get_pids(self, name):
        msg = cmds['list'].make_message(name=name)
        res = self.client.call(msg)
        return res['processes']

    def get_series(self, name, pid, field):
        stats = self.get_stats(name)
        res = []
        pid = str(pid)
        for stat in stats:
            if pid not in stat:
                continue
            res.append(stat[pid][field])
        return res

    def get_status(self, name):
        msg = cmds['status'].make_message(name=name)
        res = self.client.call(msg)
        return res['status']

    def switch_status(self, name):
        msg = cmds['status'].make_message(name=name)
        res = self.client.call(msg)
        status = res['status']
        if status == 'active':
            # stopping the watcher
            msg = cmds['stop'].make_message(name=name)
        else:
            msg = cmds['start'].make_message(name=name)
        res = self.client.call(msg)
        return res

    def add_watcher(self, name, cmd, args):
        msg = cmds['add'].make_message(name=name, cmd=cmd, args=args)
        res = self.client.call(msg)
        self.verify()  # will do better later
        return res['status'] == 'ok'
