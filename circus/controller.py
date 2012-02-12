import zmq

from circus.sighandler import SysHandler


class Controller(object):
    def __init__(self, endpoint, workers, timeout=1.0):
        self.context = zmq.Context()

        self.skt = self.context.socket(zmq.REP)
        self.skt.bind(endpoint)

        # bind the socket to internal ipc.
        self.skt.bind("ipc://workers")

        self.poller = zmq.Poller()
        self.poller.register(self.skt, zmq.POLLIN)

        self.workers = workers
        self.timeout = timeout * 1000

        # start the sys handler
        self.sys_hdl = SysHandler()

    def poll(self):
        try:
            events = dict(self.poller.poll(self.timeout))
        except zmq.ZMQError:
            return

        for socket in events:
            msg = socket.recv() or ""
            msg = msg.lower()

            if msg == 'numworkers':
                socket.send(str(len(self.workers)))
            else:
                try:
                    handler = getattr(self.workers, "handle_%s" % msg)
                    handler()
                except AttributeError:
                    print "ignored messaged %s" % msg

    def terminate(self):
        self.sys_hdl.terminate()
        try:
            self.context.destroy(0)
        except:
            pass
