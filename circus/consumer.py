import errno
import zmq

from circus.util import DEFAULT_ENDPOINT_SUB
from zmq import ssh


class CircusConsumer(object):
    def __init__(self, topics, context=None, endpoint=None, ssh_server=None):
        if endpoint is None:
            endpoint = DEFAULT_ENDPOINT_SUB

        self.topics = topics
        self.keep_context = context is not None
        self.context = context or zmq.Context()
        self.endpoint = endpoint
        self.pubsub_socket = self.context.socket(zmq.SUB)
        if ssh_server is None:
            self.pubsub_socket.connect(self.endpoint)
        else:
            ssh.tunnel_connection(self.pubsub_socket, endpoint, ssh_server)
        for topic in self.topics:
            self.pubsub_socket.setsockopt(zmq.SUBSCRIBE, topic)

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
