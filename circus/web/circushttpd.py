import os
import cgi
from collections import defaultdict
from threading import Thread
import time

try:
    from bottle import route, run, static_file, redirect, request
    from mako.lookup import TemplateLookup
except ImportError:
    raise ImportError('You need to install Bottle and Mako')

from circus.commands import get_commands
from circus.client import CircusClient, CallError


_DIR = os.path.dirname(__file__)
TMPLS = TemplateLookup(directories=[_DIR])
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


def static(filename):
    return static_file(filename, root=_DIR)


@route('/watchers/<name>/process/kill/<pid>')
def kill_process(name, pid):
    try:
        client.killproc(name, pid)
        msg = 'success'
    except CallError, e:
        msg = str(e)

    redirect('/watchers/%s?msg=%s' % (name, msg))


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



@route('/watchers/<name>/stats/<field>', method='GET')
def get_stat(name, field):
    if client is None:
        return {}
    res = {}
    try:
        pids = [str(pid) for pid in client.get_pids(name)]
        for pid in pids:
            res[pid] = [str(v) for v in client.get_series(name, pid, field)]
    except CallError:
        pass

    return res


@route('/watchers/<name>/process/decr', method='GET')
def decr_proc(name):
    url = request.query.get('redirect', '/watchers/%s' % name)
    try:
        client.decrproc(name)
        msg = 'success'
    except CallError, e:
        msg = str(e)
    redirect(url + '?msg=' + msg)

@route('/watchers/<name>/process/incr', method='GET')
def incr_proc(name):
    url = request.query.get('redirect', '/watchers/%s' % name)
    try:
        client.incrproc(name)
        msg = 'success'
    except CallError, e:
        msg = str(e)
    redirect(url + '?msg=' + msg)


@route('/watchers/<name>/switch_status', method='GET')
def switch(name):
    try:
        client.switch_status(name)
        redirect('/')
    except CallError, e:
        redirect('/?msg='+ str(e))


@route('/add_watcher', method='POST')
def add_watcher():
    try:
        if client.add_watcher(**request.POST):
            redirect('/watchers/%(name)s' % request.POST)
        else:
            redirect('/?msg=Failed')
    except CallError, e:
        redirect('/?msg=Failed')


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


@route('/disconnect')
def disconnect():
    global client

    if client is not None:
        client.stop()
        client = None
        redirect('/?msg=disconnected')


def main():
    run(host='localhost', port=8080)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
