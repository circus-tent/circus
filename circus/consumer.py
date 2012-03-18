import errno
import zmq


class CircusConsumer(object):
    def __init__(self, topics, context=None, endpoint='tcp://127.0.0.1:5556'):
        self.topics = topics
        self.context = context or zmq.Context()
        self.endpoint = endpoint
        self.pubsub_socket = self.context.socket(zmq.SUB)
        self.pubsub_socket.connect(self.endpoint)
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
        try:
            self.context.destroy(0)
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise
