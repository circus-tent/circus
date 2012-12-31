import errno
from circus import zmq

from circus.util import DEFAULT_ENDPOINT_SUB, get_connection


class CircusConsumer(object):
    def __init__(self, topics, context=None, endpoint=DEFAULT_ENDPOINT_SUB,
                 ssh_server=None, timeout=1.):
        self.topics = topics
        self.keep_context = context is not None
        self.context = context or zmq.Context()
        self.endpoint = endpoint
        self.pubsub_socket = self.context.socket(zmq.SUB)
        get_connection(self.pubsub_socket, self.endpoint, ssh_server)
        for topic in self.topics:
            self.pubsub_socket.setsockopt(zmq.SUBSCRIBE, topic)
        self.poller = zmq.Poller()
        self.poller.register(self.pubsub_socket, zmq.POLLIN)
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ On context manager exit, destroy the zmq context """
        self.stop()

    def __iter__(self):
        return self.iter_messages()

    def iter_messages(self):
        """ Yields tuples of (topic, message) """
        with self:
            while True:
                try:
                    events = dict(self.poller.poll(self.timeout * 1000))
                except zmq.ZMQError as e:
                    if e.errno == errno.EINTR:
                        continue

                if len(events) == 0:
                    continue

                topic, message = self.pubsub_socket.recv_multipart()
                yield topic, message

    def stop(self):
        if self.keep_context:
            return
        try:
            self.context.destroy(0)
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise
