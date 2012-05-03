from circus.consumer import CircusConsumer
import json


class StatsClient(CircusConsumer):
    def __init__(self, endpoint='tcp://127.0.0.1:5557', context=None):
        CircusConsumer.__init__(self, ['stat.'], context, endpoint)

    def iter_messages(self):
        """ Yields tuples of (watcher, pid, stat)"""
        with self:
            while True:
                topic, stat = self.pubsub_socket.recv_multipart()
                topic = topic.split('.')
                if len(topic) == 3:
                    __, watcher, pid = topic
                    yield watcher, long(pid), json.loads(stat)
                else:
                    __, watcher = topic
                    yield watcher, None, json.loads(stat)


TMP = ('watcher: %(watcher)s - pid: %(pid)d - cpu: %(cpu)s%% - '
       'mem: %(mem)s%%')
TMP2 = ('Summary - watcher: %(watcher)s - cpu: %(cpu)s%% - '
       'mem: %(mem)s%%')


if __name__ == '__main__':
    client = StatsClient()
    try:
        for watcher, pid, stat in client:
            stat['watcher'] = watcher
            if pid is not None:
                stat['pid'] = pid
                print TMP % stat
            else:
                print TMP2 % stat
    except KeyboardInterrupt:
        client.stop()
