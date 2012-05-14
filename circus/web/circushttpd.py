import os
import cgi
import argparse
import sys
try:
    from bottle import route, run, static_file, redirect, request
    from mako.lookup import TemplateLookup
except ImportError:
    raise ImportError('You need to install Bottle and Mako')

from circus.web.controller import LiveClient, CallError
from circus import __version__


_DIR = os.path.dirname(__file__)
TMPLS = TemplateLookup(directories=[_DIR])
client = None
MAX_STATS = 100


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
    return tmpl.render(client=client, msg=msg, version=__version__)


@route('/circusd/stats/<field>', method='GET')
def get_dstat(field):
    #start = int(request.query.get('start', '0'))
    #end = int(request.query.get('end', '-1'))

    if client is None:
        return {}
    try:
        res = {'info': [str(v) for v in client.get_dstats(field)]}
    except (CallError, KeyboardInterrupt, KeyError):
        pass
    return res


@route('/watchers/<name>/stats/<field>', method='GET')
def get_stat(name, field):
    start = int(request.query.get('start', '0'))
    end = int(request.query.get('end', '-1'))

    if client is None:
        return {}
    res = {}
    try:
        pids = [str(pid) for pid in client.get_pids(name)]
        for pid in pids:
            res[pid] = [str(v) for v in client.get_series(name, pid, field,
                        start, end)]
    except (CallError, KeyboardInterrupt, KeyError):
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
    url = request.query.get('redirect', '/')
    try:
        client.switch_status(name)
        redirect(url)
    except CallError, e:
        redirect(url + '?msg=' + str(e))


@route('/add_watcher', method='POST')
def add_watcher():
    try:
        if client.add_watcher(**request.POST):
            redirect('/watchers/%(name)s' % request.POST)
        else:
            redirect('/?msg=Failed')
    except CallError:
        redirect('/?msg=Failed')


@route('/watchers/<name>', method='GET')
def watcher(name):
    msg = request.query.get('msg')
    if msg:
        msg = cgi.escape(msg)
    tmpl = TMPLS.get_template('watcher.html')
    return tmpl.render(client=client, msg=msg, name=name, version=__version__)


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
    parser = argparse.ArgumentParser(description='Run the Web Console')
    parser.add_argument('--host', help='Host', default='localhost')
    parser.add_argument('--port', help='port', default=8080)
    parser.add_argument('--server', help='web server to use',
                        default='wsgiref')
    args = parser.parse_args()
    old = sys.argv[:]
    sys.argv[:] = []
    try:
        run(host=args.host, port=args.port, server=args.server)
    finally:
        sys.argv[:] = old


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
