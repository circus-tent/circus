import errno
import zmq
import sys
import signal

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

        # Don't let SIGQUIT and SIGUSR1 disturb active requests
        # by interrupting system calls
        if hasattr(signal, 'siginterrupt'):  # python >= 2.6
            signal.siginterrupt(signal.SIGQUIT, False)
            signal.siginterrupt(signal.SIGUSR1, False)

    def stop(self):
        try:
            self.context.destroy(0)
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise

    def call(self, cmd):
        try:
            self.socket.send(cmd)
        except zmq.ZMQError, e:
            raise CallError(str(e))

        while True:
            try:
                events = dict(self.poller.poll(self.timeout))
            except zmq.ZMQError, e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise CallError(str(e))
            else:
                break

        if len(events) == 0:
            raise CallError("Timed out")

        for socket in events:
            msg = socket.recv()
            return msg


def main():
    client = CircusClient(sys.argv[1])

    cmd_parts = sys.argv[2:]

    if len(cmd_parts) >= 2:
        cmd = " ".join(cmd_parts[:2]).lower() + " " + " ".join(cmd_parts[2:])
    else:
        cmd = cmd_parts[0].lower()

    try:
        print client.call(cmd.strip())
        sys.exit(0)
    except CallError, e:
        print str(e)
        sys.exit(1)

    finally:
        client.stop()


if __name__ == '__main__':
    main()
