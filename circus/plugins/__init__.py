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
from circus.util import debuglog, to_bool


class CircusPlugin(Thread):
    """Base class to write plugins.

    Options:

    - **context** -- the ZMQ context to use
    - **endpoint** -- the circusd ZMQ endpoint
    - **pubsub_endpoint** -- the circusd ZMQ pub/sub endpoint
    - **check_delay** -- the configured check delay
    -- **config** -- free config mapping
    """
    name = ''

    def __init__(self, context, endpoint, pubsub_endpoint, check_delay,
                 **config):
        super(CircusPlugin, self).__init__()
        self.daemon = True
        self.active = to_bool(config.get('active', True))
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
        if not self.active:
            raise ValueError('Will not start an inactive plugin')
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
        """Sends to **circusd** the command.

        Options:

        - **command** -- the command to call
        - **props** -- keywords argument to add to the call

        Returns the JSON mapping sent back by **circusd**
        """
        msg = make_message(command, **props)
        self.client.send(json.dumps(msg))
        msg = self.client.recv()
        return json.loads(msg)

    def cast(self, command, **props):
        """Fire-and-forget a command to **circusd**

        Options:

        - **command** -- the command to call
        - **props** -- keywords argument to add to the call
        """
        msg = cast_message(command, **props)
        self.client.send(json.dumps(msg))

    #
    # methods to override.
    #
    def handle_recv(self, data):
        """Receives every event published by **circusd**

        Options:

        - **data** -- a tuple containing the topic and the message.
        """
        raise NotImplementedError()

    def handle_stop(self):
        """Called right before the plugin is stopped by Circus.
        """
        pass

    def handle_init(self):
        """Called right befor a plugin is started - in the thread context.
        """
        pass
