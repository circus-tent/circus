from collections import defaultdict
import threading
from circus.commands import get_commands
from circus.client import CircusClient, CallError

try:
    from gevent import monkey, local
    if not threading.local is local.local:
        monkey.patch_all()
except ImportError:
    pass

cmds = get_commands()


class LiveClient(object):
    def __init__(self, endpoint, ssh_server=None):
        self.endpoint = str(endpoint)
        self.stats_endpoint = None
        self.client = CircusClient(endpoint=self.endpoint,
                                   ssh_server=ssh_server)
        self.connected = False
        self.watchers = []
        self.plugins = []
        self.stats = defaultdict(list)
        self.dstats = []
        self.sockets = None
        self.use_sockets = False
        self.embed_httpd = False

    def stop(self):
        self.client.stop()

    def update_watchers(self):
        """Calls circus and initialize the list of watchers.

        If circus is not connected raises an error.
        """
        self.watchers = []
        self.plugins = []

        # trying to list the watchers
        try:
            self.connected = True
            for watcher in self.client.send_message('list')['watchers']:
                if watcher in ('circusd-stats', 'circushttpd'):
                    if watcher == 'circushttpd':
                        self.embed_httpd = True
                    continue

                options = self.client.send_message('options',
                                                   name=watcher)['options']
                self.watchers.append((watcher, options))
                if watcher.startswith('plugin:'):
                    self.plugins.append(watcher)

                if not self.use_sockets and options.get('use_sockets', False):
                    self.use_sockets = True

            self.watchers.sort()
            self.stats_endpoint = self.get_global_options()['stats_endpoint']
        except CallError:
            self.connected = False

    def killproc(self, name, pid):
        # killing a proc and its children
        res = self.client.send_message('signal', name=name, pid=int(pid),
                                       signum=9, recursive=True)
        self.update_watchers()  # will do better later
        return res

    def get_option(self, name, option):
        watchers = dict(self.watchers)
        return watchers[name][option]

    def get_global_options(self):
        return self.client.send_message('globaloptions')['options']

    def get_options(self, name):
        watchers = dict(self.watchers)
        return watchers[name].items()

    def incrproc(self, name):
        res = self.client.send_message('incr', name=name)
        self.update_watchers()  # will do better later
        return res

    def decrproc(self, name):
        res = self.client.send_message('decr', name=name)
        self.update_watchers()  # will do better later
        return res

    def get_stats(self, name, start=0, end=-1):
        return self.stats[name][start:end]

    def get_dstats(self, field, start=0, end=-1):
        stats = self.dstats[start:end]
        res = []
        for stat in stats:
            res.append(stat[field])
        return res

    def get_pids(self, name):
        res = self.client.send_message('list', name=name)
        return res['pids']

    def get_sockets(self, force_reload=False):
        if not self.sockets or force_reload:
            res = self.client.send_message('listsockets')
            self.sockets = res['sockets']
        return self.sockets

    def get_series(self, name, pid, field, start=0, end=-1):
        stats = self.get_stats(name, start, end)
        res = []
        for stat in stats:
            pids = stat['pid']
            if isinstance(pids, list):
                continue
            if str(pid) == str(stat['pid']):
                res.append(stat[field])
        return res

    def get_status(self, name):
        return self.client.send_message('status', name=name)['status']

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
        res = self.client.send_message('add', name=name, cmd=cmd)
        if res['status'] == 'ok':
            # now configuring the options
            options = {}
            options['numprocesses'] = int(kw.get('numprocesses', '5'))
            options['working_dir'] = kw.get('working_dir')
            options['shell'] = kw.get('shell', 'off') == 'on'
            res = self.client.send_message('set', name=name, options=options)
            self.update_watchers()  # will do better later
        return res
