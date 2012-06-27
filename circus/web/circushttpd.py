import argparse
import os
import sys

try:
    from beaker.middleware import SessionMiddleware
    from bottle import (app, route as route_, run, static_file, redirect,
                        request, ServerAdapter)
    from mako.lookup import TemplateLookup
    from socketio import socketio_manage
    from socketio.mixins import RoomsMixin, BroadcastMixin
    from socketio.namespace import BaseNamespace

except ImportError, e:
    raise ImportError('You need to install dependencies to run the webui. '\
                    + 'You can do so by using "pip install -r '
                    + 'web-requirements.txt"\nInitial error: %s' % str(e))

from circus.web.controller import LiveClient, CallError
from circus.stats.client import StatsClient
from circus import __version__


_DIR = os.path.dirname(__file__)
TMPLS = TemplateLookup(directories=[_DIR])

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': './data',
    'session.auto': True
}

app = SessionMiddleware(app(), session_opts)

client = None


def route(*args, **kwargs):
    """Replace the default bottle route decorator and redirect to the
    connection page if the client is not defined
    """
    ensure_client = kwargs.get('ensure_client', True)

    def wrapper(func):
        def client_or_redirect(*fargs, **fkwargs):
            if ensure_client:
                global client
                if client is None:
                    session = get_session()
                    if 'endpoint' in session:
                        client = connect_to_endpoint(session['endpoint'])
                    else:
                        return redirect('/connect')
            return func(*fargs, **fkwargs)
        return route_(*args, **kwargs)(client_or_redirect)
    return wrapper


@route('/media/<filename:path>', ensure_client=False)
def get_media(filename):
    return static_file(filename, root=_DIR)


@route('/', method='GET')
def index():
    return render_template('index.html')


@route('/watchers/<name>/process/kill/<pid>')
def kill_process(name, pid):
    return run_command(
        func=client.killproc, args=(name, pid),
        message='process {pid} killed sucessfully'.format(pid=pid),
        redirect_url='/watchers/%s' % name)


@route('/watchers/<name>/process/decr', method='GET')
def decr_proc(name):
    return run_command(
        func=client.decrproc, args=(name,),
        message='removed one process from the {watcher} pool'\
                .format(watcher=name),
        redirect_url='/watchers/%s' % name)


@route('/watchers/<name>/process/incr', method='GET')
def incr_proc(name):

    return run_command(
        func=client.incrproc, args=(name,),
        message='added one process to the {watcher} pool'.format(watcher=name),
        redirect_url='/watchers/%s' % name)


@route('/watchers/<name>/switch_status', method='GET')
def switch(name):
    return run_command(func=client.switch_status, args=(name,),
                       message='status switched', redirect_url='/')


@route('/add_watcher', method='POST')
def add_watcher():
    return run_command(client.add_watcher,
                       kwargs=request.POST,
                       message='added a new watcher',
                       redirect_url='/watchers/%(name)s' % request.POST,
                       redirect_on_error='/')


@route('/watchers/<name>', method='GET')
def watcher(name):
    return render_template('watcher.html', name=name)


@route('/connect', method=['POST', 'GET'], ensure_client=False)
def connect():
    if request.method == 'GET':
        return render_template('connect.html')

    elif request.method == 'POST':
        session = get_session()
        session['endpoint'] = request.forms.endpoint
        session.save()

        client = connect_to_endpoint(request.forms.endpoint)
        if client.connected:
            message = 'You are now connected'
        else:
            message = 'Impossible to connect'
        set_message(message)
        redirect('/')


@route('/disconnect')
def disconnect():
    global client

    if client is not None:
        client.stop()
        client = None
        session = get_session()
        session.pop('endpoint')
        session.save()
        set_message('You are now disconnected')
    redirect('/')


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

        # unpack the params
        streams = msg.get('watchers', [])
        streamsWithPids = msg.get('watchersWithPids', [])

        # if we want to supervise the processes of a watcher, then send the
        # list of pids trough a socket.
        for watcher in streamsWithPids:
            pids = [int(pid) for pid in client.get_pids(watcher)]
            channel = 'stats-{watcher}-pids'.format(watcher=watcher)
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


def get_session():
    return request.environ.get('beaker.session')


def set_message(message):
    session = get_session()
    session['message'] = message
    session.save()


def set_error(message):
    return set_message("An error happened: %s" % message)


def run_command(func, message, redirect_url, redirect_on_error=None,
                args=None, kwargs=None):

    if redirect_on_error is None:
        redirect_on_error = redirect_url
    args = args or ()
    kwargs = kwargs or {}

    try:
        res = func(*args, **kwargs)
        if res['status'] != 'ok':
            message = "An error happened: %s" % res['reason']
    except CallError, e:
        message = "An error happened: %s" % e
        redirect_url = redirect_on_error

    if message:
        set_message(message)
    redirect(redirect_url)


def connect_to_endpoint(endpoint):
    client = LiveClient(endpoint=endpoint)
    client.update_watchers()
    return client


def render_template(template, **data):
    """Finds the given template and renders it with the given data.

    Also adds some data that can be useful to the template, even if not
    explicitely asked so.

    :param template: the template to render
    :param **data: the kwargs that will be passed when rendering the template
    """
    tmpl = TMPLS.get_template(template)

    # send the last message stored in the session in addition, in the "message"
    # attribute.
    server = '%s://%s' % (request.urlparts.scheme, request.urlparts.netloc)

    return tmpl.render(client=client, version=__version__,
                       session=get_session(), SERVER=server, **data)


def main():
    parser = argparse.ArgumentParser(description='Run the Web Console')
    parser.add_argument('--host', help='Host', default='0.0.0.0')
    parser.add_argument('--port', help='port', default=8080)
    parser.add_argument('--server', help='web server to use',
                        default=SocketIOServer)
    parser.add_argument('--version', action='store_true',
                     default=False, help='Displays Circus version and exits.')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    run(app, host=args.host, port=args.port, server=args.server)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
