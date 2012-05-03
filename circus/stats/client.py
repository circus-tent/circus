from circus.consumer import CircusConsumer


class StatsClient(CircusConsumer):
    def __init__(self, endpoint='tcp://127.0.0.1:5557', context=None):
        CircusConsumer.__init__(self, ['pid.'], context, endpoint)

    def iter_messages(self):
        """ Yields tuples of (pid, info)"""
        with self:
            while True:
                topic, info = self.pubsub_socket.recv_multipart()
                pid = topic.split('.')[-1]
                yield long(pid), info


if __name__ == '__main__':
    client = StatsClient()
    try:
        for pid, info in client:
            print '%d: %s' % (pid, info)
    except KeyboardInterrupt:
        client.stop()
