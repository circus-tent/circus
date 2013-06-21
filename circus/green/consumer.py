from circus.consumer import CircusConsumer as _CircusConsumer

from zmq.green import Context, Poller, POLLIN


class CircusConsumer(_CircusConsumer):
    def _init_context(self, context):
        self.context = context or Context()

    def _init_poller(self):
        self.poller = Poller()
        self.poller.register(self.pubsub_socket, POLLIN)
