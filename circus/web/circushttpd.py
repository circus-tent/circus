import os
import cgi

from bottle import route, run, static_file, redirect, request

from mako.lookup import TemplateLookup
from mako.template import Template

from circus.commands import get_commands
from circus.client import CircusClient, CallError


_DIR = os.path.dirname(__file__)
TMPLS = TemplateLookup(directories=[_DIR])
client = None
cmds = get_commands()


class LiveClient(object):
    def __init__(self, endpoint):
        self.endpoint = str(endpoint)
        self.client = CircusClient(endpoint=self.endpoint)
        self.connected = False
        self.watchers = []

    def verify(self):
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
        except CallError:
            self.connected = False



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
