# -*- coding: utf-8 -
import uuid

import zmq
from zmq.utils.jsonapi import jsonmod as json
from zmq.eventloop.zmqstream import ZMQStream

from circus.exc import CallError
from circus.py3compat import string_types
from circus.util import get_connection
from circus.client import CircusClient, make_message

from collections import defaultdict

from datetime import timedelta

from tornado import gen


class AsyncClient(CircusClient):
    """
    An asynchronous circus client implementation designed to works with tornado
    IOLoop
    """
    def __init__(self, loop, endpoint, context=None, timeout=5.0,
                 ssh_server=None, ssh_keyfile=None):
        self.context = context or zmq.Context.instance()
        self.ssh_server = ssh_server
        self.ssh_keyfile = ssh_keyfile
        self._timeout = timeout
        self.timeout = timeout * 1000
        self.loop = loop
        self.endpoint = endpoint

        # Infos
        self.stats_endpoint = None
        self.connected = False
        self.watchers = []
        self.plugins = []
        self.stats = defaultdict(list)
        self.dstats = []
        self.sockets = None
        self.use_sockets = False
        self.embed_httpd = False

        # Connection counter
        self.count = 0

    def send_message(self, command, callback=None, **props):
        return self.call(make_message(command, **props), callback)

    def call(self, cmd, callback):
        if not isinstance(cmd, string_types):
            try:
                cmd = json.dumps(cmd)
            except ValueError as e:
                raise CallError(str(e))

        socket = self.context.socket(zmq.DEALER)
        socket.setsockopt(zmq.IDENTITY, uuid.uuid4().hex)
        socket.setsockopt(zmq.LINGER, 0)
        get_connection(socket, self.endpoint, self.ssh_server,
                       self.ssh_keyfile)

        if callback:
            stream = ZMQStream(socket, self.loop)

            def timeout_callback():
                stream.stop_on_recv()
                stream.close()
                raise CallError('Call timeout for cmd', cmd)

            timeout = self.loop.add_timeout(timedelta(seconds=5),
                                            timeout_callback)

            def recv_callback(msg):
                self.loop.remove_timeout(timeout)
                stream.stop_on_recv()
                stream.close()
                callback(json.loads(msg[0]))

            stream.on_recv(recv_callback)

        try:
            socket.send(cmd)
        except zmq.ZMQError, e:
            raise CallError(str(e))

        if not callback:
            return json.loads(socket.recv())

    @gen.coroutine
    def update_watchers(self):
        """Calls circus and initialize the list of watchers.

        If circus is not connected raises an error.
        """
        self.watchers = []
        self.plugins = []

        # trying to list the watchers
        try:
            self.connected = True
            watchers = yield gen.Task(self.send_message, 'list')
            watchers = watchers['watchers']

            for watcher in watchers:
                if watcher in ('circusd-stats', 'circushttpd'):
                    if watcher == 'circushttpd':
                        self.embed_httpd = True
                    continue

                options = yield gen.Task(self.send_message, 'options',
                                         name=watcher)
                options = options['options']

                self.watchers.append((watcher, options))
                if watcher.startswith('plugin:'):
                    self.plugins.append(watcher)

                if not self.use_sockets and options.get('use_sockets', False):
                    self.use_sockets = True

            self.watchers.sort()
            global_options = yield gen.Task(self.get_global_options)
            self.stats_endpoint = global_options['stats_endpoint']
            if self.endpoint.startswith('tcp://'):
                # In case of multi interface binding i.e: tcp://0.0.0.0:5557
                anyaddr = '0.0.0.0'
                ip = self.endpoint.lstrip('tcp://').split(':')[0]
                self.stats_endpoint = self.stats_endpoint.replace(anyaddr, ip)
        except CallError:
            self.connected = False
            raise

    @gen.coroutine
    def get_global_options(self):
        res = yield gen.Task(self.send_message, 'globaloptions')
        raise gen.Return(res['options'])
