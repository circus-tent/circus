from circus.client import CircusClient as _CircusClient

from zmq.green import Context, Poller, POLLIN


class CircusClient(_CircusClient):
    def _init_context(self, context):
        self.context = context or Context.instance()

    def _init_poller(self):
        self.poller = Poller()
        self.poller.register(self.socket, POLLIN)
