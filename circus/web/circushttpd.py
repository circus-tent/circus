import os
import cgi
import argparse
import sys

try:
    from bottle import (route, run, static_file, redirect, request,
                        ServerAdapter)
    from mako.lookup import TemplateLookup
    from socketio import socketio_manage
    from socketio.namespace import BaseNamespace
    from socketio.mixins import RoomsMixin, BroadcastMixin

except ImportError:
    raise ImportError('You need to install Bottle, Mako and gevent-socketio. '
                    + 'You can do so using "pip install -r '
                    + 'web-requirements.txt"')

from circus.web.controller import LiveClient, CallError
from circus.stats.client import StatsClient
from circus import __version__


_DIR = os.path.dirname(__file__)
TMPLS = TemplateLookup(directories=[_DIR])

client = None


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
    return render_template('index.html', msg=msg)


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
    return render_template('watcher.html', msg=msg, name=name)


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


@route('/socket.io/<someid>/websocket/<socket_id>', method='GET')
def socketio(someid, socket_id):
    return socketio_manage(request.environ, {'': StatsNamespace})


class StatsNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):
    def on_get_stats(self, msg):
        """This method is the one way to start a conversation with the socket.
        When sending a message here, the parameters are packt into the msg
        dictionary, which contains:

            - "streams", a list of streams that the client want to be notified
              about.
            - "get_processes", if it wants to include the subprocesses managed
              by this watcher or not (optional, defaults to False)

        The server sends back to the client some messages, on different
        channels:

            - "stats-<watchername>" sends memory and cpu info for the
              aggregation of stats.
            - stats-<watchername>-pids sends the list of pids for this watcher
            - "stats-<watchername>-<pid>" sends the information about
              specific pids for the different watchers (works only if
              "get_processes" is set to True when calling this method)
        """

        print msg
        # unpack the params
        streams = msg.get('watchers', [])
        streamsWithPids = msg.get('watchersWithPids', [])

        # if we want to supervise the processes of a watcher, then send the
        # list of pids trough a socket.
        for watcher in streamsWithPids:
            pids = [int(pid) for pid in client.get_pids(watcher)]
            channel = 'stats-{watcher}-pids'.format(watcher=watcher)
            print channel
            self.send_data(channel, pids=pids)

        # Get the channels that are interesting to us and send back information
        # there when we got them.
        stats = StatsClient(endpoint=client.stats_endpoint)
        for watcher, pid, stat in stats:
            if watcher in streams or watcher in streamsWithPids:
                if pid is None:  # means that it's the aggregation
                    self.send_data('stats-{watcher}'.format(watcher=watcher),
                                   mem=stat['mem'], cpu=stat['cpu'])
                else:
                    if watcher in streamsWithPids:
                        self.send_data('stats-{watcher}-{pid}'\
                                       .format(watcher=watcher, pid=pid),
                                       mem=stat['mem'], cpu=stat['cpu'])

    def send_data(self, topic, **kwargs):
        """Send the given dict encoded into json to the listening socket on the
        browser side.

        :param topic: the topic to send the information to
        :param **kwargs: the dict to serialize and send
        """
        pkt = dict(type="event", name=topic, args=kwargs,
                   endpoint=self.ns_name)
        self.socket.send_packet(pkt)


# Utils

class SocketIOServer(ServerAdapter):
    def run(self, handler):
        try:
            from socketio.server import SocketIOServer
        except ImportError:
            raise ImportError('You need to install gevent_socketio')

        from gevent import monkey
        from gevent_zeromq import monkey_patch
        monkey.patch_all()
        monkey_patch()

        namespace = self.options.get('namespace', 'socket.io')
        policy_server = self.options.get('policy_server', False)
        socket_server = SocketIOServer((self.host, self.port), handler,
                                       namespace=namespace,
                                       policy_server=policy_server)
        handler.socket_server = socket_server
        socket_server.serve_forever()


def render_template(template, **data):
    """Finds the given template and renders it with the given data.

    Also adds some data that can be useful to the template, even if not
    explicitely asked so.

    :param template: the template to render
    :param **data: the kwargs that will be passed when rendering the template
    """
    tmpl = TMPLS.get_template(template)
    return tmpl.render(client=client, version=__version__, **data)


def main():
    parser = argparse.ArgumentParser(description='Run the Web Console')
    parser.add_argument('--host', help='Host', default='localhost')
    parser.add_argument('--port', help='port', default=8080)
    parser.add_argument('--server', help='web server to use',
                        default=SocketIOServer)
    parser.add_argument('--version', action='store_true',
                     default=False, help='Displays Circus version and exits.')

    args = parser.parse_args()
    old = list(sys.argv)
    sys.argv = []

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    try:
        run(host=args.host, port=args.port, server=args.server)
    finally:
        sys.argv = old


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
