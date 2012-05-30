""" Base class to create Circus subscribers plugins.
"""
import errno
from threading import Thread
import uuid

import zmq
from zmq.eventloop import ioloop, zmqstream
from zmq.utils.jsonapi import jsonmod as json

from circus import logger
from circus.client import make_message, cast_message
from circus.util import debuglog


class CircusPlugin(Thread):

    name = ''

    def __init__(self, context, endpoint, pubsub_endpoint, check_delay):
        super(CircusPlugin, self).__init__()
        self.daemon = True
        self.context = context
        self.pubsub_endpoint = pubsub_endpoint
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.loop = ioloop.IOLoop()
        self._id = uuid.uuid4().hex    # XXX os.getpid()+thread id is enough...
        self.running = False

    @debuglog
    def initialize(self):
        self.client = self.context.socket(zmq.DEALER)
        self.client.setsockopt(zmq.IDENTITY, self._id)
        self.client.connect(self.endpoint)
        self.client.linger = 0
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b'watcher.')
        self.sub_socket.connect(self.pubsub_endpoint)
        self.substream = zmqstream.ZMQStream(self.sub_socket, self.loop)
        self.substream.on_recv(self.handle_recv)

    @debuglog
    def run(self):
        self.handle_init()
        self.initialize()
        self.running = True
        while True:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                logger.debug(str(e))

                if e.errno == errno.EINTR:
                    continue
                elif e.errno == zmq.ETERM:
                    break
                else:
                    logger.debug("got an unexpected error %s (%s)", str(e),
                                 e.errno)
                    raise
            else:
                break
        self.client.close()
        self.sub_socket.close()

    @debuglog
    def stop(self):
        if not self.running:
            return

        try:
            self.handle_stop()
        finally:
            self.loop.stop()
            self.join()

        self.running = False

    def call(self, command, **props):
        msg = make_message(command, **props)
        self.client.send(json.dumps(msg))
        msg = self.client.recv()
        return json.loads(msg)

    def cast(self, command, **props):
        msg = cast_message(command, **props)
        self.client.send(json.dumps(msg))

    #
    # methods to override.
    #
    def handle_recv(self, data):
        raise NotImplementedError()

    def handle_stop(self):
        pass

    def handle_init(self):
        pass
