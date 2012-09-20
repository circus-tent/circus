# -*- coding: utf-8 -
import errno
import uuid
from circus import zmq

from circus.exc import CallError
from circus.py3compat import string_types
from circus.util import DEFAULT_ENDPOINT_DEALER, get_connection
from zmq.utils.jsonapi import jsonmod as json


def make_message(command, **props):
    return {"command": command, "properties": props or {}}


def cast_message(command, **props):
    return {"command": command, "msg_type": "cast", "properties": props or {}}


def make_json(command, **props):
    return json.dumps(make_message(command, **props))


class CircusClient(object):
    def __init__(self, context=None, endpoint=DEFAULT_ENDPOINT_DEALER,
                 timeout=5.0, ssh_server=None):
        self.context = context or zmq.Context.instance()
        self.endpoint = endpoint
        self._id = uuid.uuid4().hex
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self._id)
        self.socket.setsockopt(zmq.LINGER, 0)
        get_connection(self.socket, endpoint, ssh_server)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self._timeout = timeout
        self.timeout = timeout * 1000

    def stop(self):
        self.socket.close()

    def send_message(self, command, **props):
        return self.call(make_message(command, **props))

    def call(self, cmd):
        if not isinstance(cmd, string_types):
            try:
                cmd = json.dumps(cmd)
            except ValueError as e:
                raise CallError(str(e))

        try:
            self.socket.send(cmd)
        except zmq.ZMQError, e:
            raise CallError(str(e))

        while True:
            try:
                events = dict(self.poller.poll(self.timeout))
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise CallError(str(e))
            else:
                break

        if len(events) == 0:
            raise CallError("Timed out.")

        for socket in events:
            msg = socket.recv()
            try:
                return json.loads(msg)
            except ValueError as e:
                raise CallError(str(e))
