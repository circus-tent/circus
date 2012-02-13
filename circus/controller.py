import os
import tempfile
import zmq

from circus.sighandler import SysHandler


class Controller(object):
    def __init__(self, endpoint, manager, timeout=1.0, ipc_prefix=None):
        self.context = zmq.Context()

        self.skt = self.context.socket(zmq.REP)
        self.skt.bind(endpoint)

        # bind the socket to internal ipc.
        ipc_name = "circus-ipc-%s" % os.getpid()
        if not ipc_prefix:
            ipc_prefix = tempfile.gettempdir()
        ipc_path = os.path.join(os.path.dirname(ipc_prefix), ipc_name)
        self.skt.bind("ipc://%s" % ipc_path)

        self.poller = zmq.Poller()
        self.poller.register(self.skt, zmq.POLLIN)

        self.manager = manager
        self.timeout = timeout * 1000

        # start the sys handler
        self.sys_hdl = SysHandler(ipc_path)

    def poll(self):
        try:
            events = dict(self.poller.poll(self.timeout))
        except zmq.ZMQError:
            return

        for socket in events:
            msg = socket.recv() or ""
            msg = msg.lower()

            if msg == 'numworkers':
                socket.send(str(self.manager.num_workers()))
            else:
                try:
                    handler = getattr(self.manager, "handle_%s" % msg)
                    handler()
                except AttributeError:
                    print "ignored messaged %s" % msg

    def terminate(self):
        self.sys_hdl.terminate()
        try:
            self.context.destroy(0)
        except:
            pass
