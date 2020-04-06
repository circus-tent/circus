import zmq
import zmq.utils.jsonapi as json

from circus import logger
from circus.util import to_bytes


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
            topic = 'stat.%s' % str(name)
            if 'subtopic' in stat:
                topic += '.%d' % stat['subtopic']

            stat = json.dumps(stat)
            logger.debug('Sending %s' % stat)
            self.socket.send_multipart([to_bytes(topic), stat])

        except zmq.ZMQError:
            if self.socket.closed:
                pass
            else:
                raise

    def stop(self):
        if self.destroy_context:
            self.ctx.destroy(0)
        logger.debug('Publisher stopped')
