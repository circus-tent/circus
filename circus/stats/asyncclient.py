import errno
import json
import zmq

from zmq.eventloop.zmqstream import ZMQStream

from circus.util import DEFAULT_ENDPOINT_SUB, get_connection


class AsyncStatsConsumer(object):
    def __init__(self, topics, loop, callback, context=None,
                 ssh_server=None, timeout=1.):
        self.topics = topics
        self.keep_context = context is not None
        self.context = context or zmq.Context()
        self.pubsub_socket = self.context.socket(zmq.SUB)
        for topic in self.topics:
            self.pubsub_socket.setsockopt(zmq.SUBSCRIBE, topic)
        self.stream = ZMQStream(self.pubsub_socket, loop)
        self.stream.on_recv(self.process_message)
        self.callback = callback
        self.timeout = timeout
        self.ssh_server = ssh_server

        # Connection counter
        self.count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ On context manager exit, destroy the zmq context """
        self.stop()

    def connect(self, endpoint):
        get_connection(self.pubsub_socket, endpoint, self.ssh_server)

    def process_message(self, msg):
        topic, stat = msg

        topic = topic.split('.')
        if len(topic) == 3:
            __, watcher, subtopic = topic
            self.callback(watcher, subtopic, json.loads(stat), self.endpoint)
        elif len(topic) == 2:
            __, watcher = topic
            self.callback(watcher, None, json.loads(stat), self.endpoint)

    def stop(self):
        self.stream.stop_on_recv()
        if self.keep_context:
            return
        try:
            self.context.destroy(0)
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise
