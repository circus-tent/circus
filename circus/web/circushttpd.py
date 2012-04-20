import os
import cgi
from collections import defaultdict

try:
    from bottle import route, run, static_file, redirect, request, response
    from mako.lookup import TemplateLookup
    from mako.template import Template
except ImportError:
    raise ImportError('You need to install Bottle and Mako')

from circus.commands import get_commands
from circus.client import CircusClient, CallError


_DIR = os.path.dirname(__file__)
TMPLS = TemplateLookup(directories=[_DIR])
client = None
cmds = get_commands()
MAX_STATS = 100


class LiveClient(object):
    def __init__(self, endpoint):
        self.endpoint = str(endpoint)
        self.client = CircusClient(endpoint=self.endpoint)
        self.connected = False
        self.watchers = []
        self.stats = defaultdict(list)

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
                self.collectstats(watcher)
            self.watchers.sort()
        except CallError:
            self.connected = False

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

    def collectstats(self, name):
        msg = cmds['stats'].make_message(name=name)
        res = self.client.call(msg)
        self.stats[name].insert(0, res['info'])
        if len(self.stats[name]) > MAX_STATS:
            self.stats[name][:] = self.stats[name][:MAX_STATS]

    def get_stats(self, name):
        self.collectstats(name)
        return self.stats[name]

    def get_pids(self, name):
        msg = cmds['list'].make_message(name=name)
        res = self.client.call(msg)
        return res['processes']

    def get_series(self, name, pid, field):
        self.collectstats(name)
        stats = self.get_stats(name)
        res = []
        pid = str(pid)
        for stat in stats:
            if pid not in stat:
                continue
            res.append(stat[pid][field])
        return res

    def get_status(self, name):
        # XXX will return a general status -- 'green' or 'red'
        return 'green'


def static(filename):
    return static_file(filename, root=_DIR)


@route('/media/<filename:path>')
def get_media(filename):
    return static_file(filename, root=_DIR)


@route('/', method='GET')
def index():
    msg = request.query.get('msg')
    if msg:
        msg = cgi.escape(msg)
    tmpl = TMPLS.get_template('index.html')
    return tmpl.render(client=client, msg=msg)


@route('/watchers/<name>/stats', method='GET')
def incr_proc(name):
    client.collectstats(name)
    redirect('/watchers/%s' % name)


@route('/watchers/<name>/stats/<field>', method='GET')
def get_stat(name, field):
    if client is None:
        return {}
    client.collectstats(name)
    pids = [str(pid) for pid in client.get_pids(name)]
    res = {}
    for pid in pids:
        res[pid] = [str(v) for v in client.get_series(name, pid, field)]
    return res


@route('/watchers/<name>/process/decr', method='GET')
def incr_proc(name):
    client.decrproc(name)
    redirect('/watchers/%s' % name)


@route('/watchers/<name>/process/incr', method='GET')
def incr_proc(name):
    client.incrproc(name)
    redirect('/watchers/%s' % name)


@route('/watchers/<name>', method='GET')
def watcher(name):
    msg = request.query.get('msg')
    if msg:
        msg = cgi.escape(msg)
    tmpl = TMPLS.get_template('watcher.html')
    return tmpl.render(client=client, msg=msg, name=name)


@route('/connect', method='POST')
def connect():
    endpoint = request.forms.endpoint
    global client
    _client = LiveClient(endpoint=endpoint)
    _client.verify()
    if _client.connected:
        client = _client
        redirect('/?msg=Connected')
    else:
        redirect('/?msg=Failed to connect')


def main():
    run(host='localhost', port=8080)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
