import threading
import zmq
import Queue
import json

from circus import logger


class StatsPublisher(threading.Thread):
    def __init__(self, streamer, stats_endpoint='tcp://127.0.0.1:5557',
                 delay=0.1, context=None):
        threading.Thread.__init__(self)
        self.streamer = streamer
        self.running = False
        self.daemon = True
        self.delay = delay
        self.ctx = context or zmq.Context()
        self.destroy_context = context is None
        self.stats_endpoint = stats_endpoint
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(self.stats_endpoint)
        self.socket.linger = 0

    def run(self):
        self.running = True
        results = self.streamer.results
        logger.debug('Starting the Publisher')
        while self.running:
            try:
                watcher, pid, stat = results.get(timeout=self.delay)
                topic = b'stat.%s' % str(watcher)
                if pid is not None:
                    topic += '.%d' % pid
                self.socket.send_multipart([topic, json.dumps(stat)])
            except zmq.ZMQError:
                if self.socket.closed:
                    self.running = False
                else:
                    raise
            except Queue.Empty:
                pass
            except Exception:
                logger.exception('Failed to some data from the queue')

    def stop(self):
        self.running = False
        if self.destroy_context:
            self.ctx.destroy(0)
        logger.debug('Publisher stopped')
