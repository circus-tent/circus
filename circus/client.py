# -*- coding: utf-8 -

import errno
import uuid

import zmq

from circus.exc import CallError


class CircusClient(object):
    def __init__(self, context=None, endpoint='tcp://127.0.0.1:5555',
            timeout=5.0):

        self.context = context or zmq.Context()

        self._id = uuid.uuid4().hex
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self._id)
        self.socket.setsockopt(zmq.LINGER, 0)

        self.socket.connect(endpoint)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.timeout = timeout * 1000

    def stop(self):
        if self.context.closed:
            return

        try:
            self.context.destroy()
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise

    def call(self, cmd):
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
            raise CallError("Timed out")

        for socket in events:
            msg = socket.recv()
            return msg
