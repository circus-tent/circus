import errno
import uuid

import zmq
import zmq.utils.jsonapi as json
from zmq.eventloop.zmqstream import ZMQStream
import tornado
from tornado import concurrent

from circus.exc import CallError
from circus.util import DEFAULT_ENDPOINT_DEALER, get_connection, to_bytes


def make_message(command, **props):
    return {"command": command, "properties": props or {}}


def cast_message(command, **props):
    return {"command": command, "msg_type": "cast", "properties": props or {}}


def make_json(command, **props):
    return json.dumps(make_message(command, **props))


class AsyncCircusClient(object):

    def __init__(self, context=None, endpoint=DEFAULT_ENDPOINT_DEALER,
                 timeout=5.0, ssh_server=None, ssh_keyfile=None):
        self._init_context(context)
        self.endpoint = endpoint
        self._id = to_bytes(uuid.uuid4().hex)
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self._id)
        self.socket.setsockopt(zmq.LINGER, 0)
        get_connection(self.socket, endpoint, ssh_server, ssh_keyfile)
        self._timeout = timeout
        self.timeout = timeout * 1000
        self.stream = ZMQStream(self.socket, tornado.ioloop.IOLoop.current())

    def _init_context(self, context):
        self.context = context or zmq.Context.instance()

    def stop(self):
        self.stream.stop_on_recv()
        # only supported by libzmq >= 3
        if hasattr(self.socket, 'disconnect'):
            self.socket.disconnect(self.endpoint)
        self.stream.close()

    @tornado.gen.coroutine
    def send_message(self, command, **props):
        res = yield self.call(make_message(command, **props))
        raise tornado.gen.Return(res)

    @tornado.gen.coroutine
    def call(self, cmd):
        if isinstance(cmd, str):
            raise DeprecationWarning('call() takes a mapping')

        call_id = uuid.uuid4().hex
        cmd['id'] = call_id
        try:
            cmd = json.dumps(cmd)
        except ValueError as e:
            raise CallError(str(e))

        try:
            future = concurrent.Future()

            def cb(msg, status):
                future.set_result(msg)
            self.stream.send(cmd, callback=cb)
            yield future
        except zmq.ZMQError as e:
            raise CallError(str(e))

        while True:
            future = concurrent.Future()
            self.stream.on_recv(future.set_result)
            messages = yield future

            for message in messages:
                try:
                    res = json.loads(message)
                    if res.get('id') != call_id:
                        # we got the wrong message
                        continue
                    raise tornado.gen.Return(res)
                except ValueError as e:
                    raise CallError(str(e))


class CircusClient(object):
    def __init__(self, context=None, endpoint=DEFAULT_ENDPOINT_DEALER,
                 timeout=5.0, ssh_server=None, ssh_keyfile=None):
        self._init_context(context)
        self.endpoint = endpoint
        self._id = to_bytes(uuid.uuid4().hex)
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self._id)
        self.socket.setsockopt(zmq.LINGER, 0)
        get_connection(self.socket, endpoint, ssh_server, ssh_keyfile)
        self._init_poller()
        self._timeout = timeout
        self.timeout = timeout * 1000

    def _init_context(self, context):
        self.context = context or zmq.Context.instance()

    def _init_poller(self):
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def stop(self):
        # only supported by libzmq >= 3
        if hasattr(self.socket, 'disconnect'):
            self.socket.disconnect(self.endpoint)
        self.socket.close()

    def send_message(self, command, **props):
        return self.call(make_message(command, **props))

    def call(self, cmd):
        if isinstance(cmd, str):
            raise DeprecationWarning('call() takes a mapping')

        call_id = uuid.uuid4().hex
        cmd['id'] = call_id
        try:
            cmd = json.dumps(cmd)
        except ValueError as e:
            raise CallError(str(e))

        try:
            self.socket.send(cmd)
        except zmq.ZMQError as e:
            raise CallError(str(e))

        while True:
            try:
                events = dict(self.poller.poll(self.timeout))
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    print(str(e))
                    raise CallError(str(e))

            if len(events) == 0:
                raise CallError("Timed out.")

            for socket in events:
                msg = socket.recv()
                try:
                    res = json.loads(msg)
                    if res.get('id') != call_id:
                        # we got the wrong message
                        continue
                    return res
                except ValueError as e:
                    raise CallError(str(e))
