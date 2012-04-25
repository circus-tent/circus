import os
from collections import defaultdict
from threading import Thread
import time
from circus.commands import get_commands
from circus.client import CircusClient, CallError


_DIR = os.path.dirname(__file__)
client = None
cmds = get_commands()
MAX_STATS = 25


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
                try:
                    res = call(msg)
                except CallError:
                    continue
                stats[name].append(res['info'])
                if len(stats[name]) > MAX_STATS:
                    start = len(stats[name]) - MAX_STATS
                    stats[name][:] = stats[name][start:]

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
        msg = cmds['signal'].make_message(name=name, process=int(pid),
                signum=9)
        res = self.client.call(msg)
        self.verify()  # will do better later
        return res['status'] == 'ok'

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

    def get_stats(self, name, start=0, end=-1):
        return self.stats[name][start:end]

    def get_pids(self, name):
        msg = cmds['list'].make_message(name=name)
        res = self.client.call(msg)
        return res['processes']

    def get_series(self, name, pid, field, start=0, end=-1):
        stats = self.get_stats(name, start, end)
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

    def add_watcher(self, name, cmd, **kw):
        msg = cmds['add'].make_message(name=name, cmd=cmd)
        res = self.client.call(msg)
        if res['status'] == 'ok':
            # now configuring the options
            options = {}
            options['numprocesses'] = int(kw.get('numprocesses', '5'))
            options['working_dir'] = kw.get('working_dir')
            options['shell'] = kw.get('shell', 'off') == 'on'
            msg = cmds['set'].make_message(name=name, options=options)
            res = self.client.call(msg)
            self.verify()  # will do better later
            return res['status'] == 'ok'
        else:
            return False
