import errno
import json
import zmq
import sys
import signal

import uuid

class CallError(Exception):
    pass


class CircusClient(object):
    def __init__(self, endpoint='tcp://127.0.0.1:5555', timeout=5.0):
        self.context = zmq.Context()

        self._id = uuid.uuid4().hex
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self._id)

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
            except zmq.ZMQError as e:
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

class CircusConsumer(object):
    def __init__(self, topics, endpoint='tcp://127.0.0.1:5556', timeout=5.0):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(endpoint)
        for topic in topics:
            self.socket.setsockopt(zmq.SUBSCRIBE, topic)


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
                topic, raw_message = self.socket.recv_multipart()
                message = json.loads(raw_message)
                yield topic, message

    def start(self):
        try:
            while True:
                try:
                    topic, msg = self.socket.recv_multipart()
                    print '   %s: %s' % (topic, json.loads(msg))
                except zmq.ZMQError as e:
                    raise CallError(str(e))

        except KeyboardInterrupt:
            pass

    def stop(self):
        try:
            self.context.destroy(0)
        except zmq.ZMQError as e:
            if e.errno == errno.EINTR:
                pass
            else:
                raise

def main():

    if sys.argv[1] == "listen":
        if len(sys.argv) < 3:
            sys.stderr.write("incorrect usage")
            sys.exit(1)
        else:
            if len(sys.argv) > 3:
                topics = sys.argv[2:]
            else:
                topics = ['']

            for message, topic in CircusConsumer(topics, sys.argv[2]):
                print message, topic

    else:
        client = CircusClient(sys.argv[1])
        cmd_parts = sys.argv[2:]

        if len(cmd_parts) >= 2:
            cmd = " ".join(cmd_parts[:2]).lower() + " " + " ".join(cmd_parts[2:])
        else:
            cmd = cmd_parts[0].lower()

        try:
            print client.call(cmd.strip())
            sys.exit(0)
        except CallError as e:
            print str(e)
            sys.exit(1)

        finally:
            client.stop()


if __name__ == '__main__':
    main()
