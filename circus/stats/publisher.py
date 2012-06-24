import zmq
import json

from circus import logger


class StatsPublisher(object):
    def __init__(self, stats_endpoint='tcp://127.0.0.1:5557', context=None):
        self.ctx = context or zmq.Context()
        self.destroy_context = context is None
        self.stats_endpoint = stats_endpoint
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(self.stats_endpoint)
        self.socket.linger = 0

    def publish(self, name, stat):
        try:
            topic = b'stat.%s' % str(name)
            if 'subtopic' in stat:
                topic += '.%d' % stat['subtopic']

            self.socket.send_multipart([topic, json.dumps(stat)])

        except zmq.ZMQError:
            if self.socket.closed:
                pass
            else:
                raise

    def stop(self):
        if self.destroy_context:
            self.ctx.destroy(0)
        logger.debug('Publisher stopped')
