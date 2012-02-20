import zmq
import sys


class CallError(Exception):
    pass

class CircusClient(object):
    def __init__(self, endpoint, timeout=5.0):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(endpoint)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.timeout = timeout * 1000

    def terminate(self):
        self.context.destroy(0)

    def call(self, cmd):
        try:
            self.socket.send(cmd)
        except zmq.ZMQError, e:
            raise CallError(str(e))

        try:
            events = dict(self.poller.poll(self.timeout))
        except zmq.ZMQError, e:
            raise CallError(str(e))

        if len(events) == 0:
            raise CallError("Timed out")

        for socket in events:
            msg = socket.recv()
            return msg


def main():
    client = CircusClient(sys.argv[1])
    try:
        print client.call(" ".join(sys.argv[2:]).lower())
        sys.exit(0)
    except CallError, e:
        print str(e)
        sys.exit(1)

    finally:
        client.terminate()

if __name__ == '__main__':
    main()
