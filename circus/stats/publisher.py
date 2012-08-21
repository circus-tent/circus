import zmq
import json

from circus import logger


class StatsPublisher(object):
    def __init__(self, stats_endpoint='tcp://127.0.0.1:5557', context=None, node_name=None):
        self.ctx = context or zmq.Context()
        self.destroy_context = context is None
        self.stats_endpoint = stats_endpoint
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(self.stats_endpoint)
        self.socket.linger = 0
        self.node_name = node_name

    def publish(self, name, stat):
        try:
            if self.node_name is not None:
                stat['node_name'] = self.node_name
            topic = b'stat.%s' % str(name)
            if 'subtopic' in stat:
                topic += '.%d' % stat['subtopic']

            stat = json.dumps(stat)
            logger.debug('Sending %s' % stat)
            self.socket.send_multipart([topic, stat])

        except zmq.ZMQError:
            if self.socket.closed:
                pass
            else:
                raise

    def stop(self):
        if self.destroy_context:
            self.ctx.destroy(0)
        logger.debug('Publisher stopped')
