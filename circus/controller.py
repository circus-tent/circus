import zmq


class Controller(object):
    def __init__(self, endpoint, workers, timeout=1.):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(endpoint)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.workers = workers
        self.timeout = timeout * 1000

    def poll(self):
        try:
            events = dict(self.poller.poll(self.timeout))
        except zmq.ZMQError:
            return

        for socket in events:
            msg = socket.recv()

            if msg == 'NUMWORKERS':
                socket.send(str(len(self.workers)))
            else:
                raise NotImplementedError()

    def terminate(self):
        self.context.destroy(0)
