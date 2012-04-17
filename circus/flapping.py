import errno
from threading import Thread, Timer
import time
import uuid

import zmq
from zmq.eventloop import ioloop, zmqstream
from zmq.utils.jsonapi import jsonmod as json

from circus import logger
from circus.client import make_message
from circus.util import debuglog


class Flapping(Thread):

    def __init__(self, context, endpoint, pubsub_endpoint, check_delay):
        super(Flapping, self).__init__()
        self.daemon = True
        self.context = context
        self.pubsub_endpoint = pubsub_endpoint
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.loop = ioloop.IOLoop()
        self._id = uuid.uuid4().hex
        self.timelines = {}
        self.timers = {}
        self.configs = {}
        self.tries = {}

    @debuglog
    def initialize(self):
        self.client = self.context.socket(zmq.DEALER)
        self.client.setsockopt(zmq.IDENTITY, self._id)
        self.client.connect(self.endpoint)
        self.client.linger = 0
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b'watcher.')
        self.sub_socket.connect(self.pubsub_endpoint)
        self.substream = zmqstream.ZMQStream(self.sub_socket, self.loop)
        self.substream.on_recv(self.handle_recv)

    @debuglog
    def run(self):
        self.initialize()
        logger.debug('Flapping entering loop mode.')
        while True:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                logger.debug(str(e))

                if e.errno == errno.EINTR:
                    continue
                elif e.errno == zmq.ETERM:
                    break
                else:
                    logger.debug("got an unexpected error %s (%s)", str(e),
                                 e.errno)
                    raise
            else:
                break
        self.client.close()
        self.sub_socket.close()

    @debuglog
    def stop(self):
        for _, timer in self.timers.items():
            timer.cancel()
        self.loop.stop()
        self.join()

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = topic.split(".")
        if topic_parts[2] == "reap":
            timeline = self.timelines.get(topic_parts[1], [])
            timeline.append(time.time())
            self.timelines[topic_parts[1]] = timeline

            self.check(topic_parts[1])
        elif topic_parts[2] == "updated":
            self.update_conf(topic_parts[1])

    def call(self, cmd):
        self.client.send(json.dumps(cmd))
        msg = self.client.recv()
        return json.loads(msg)

    def cast(self, cmd):
        self.client.send(json.dumps(cmd))

    def update_conf(self, watcher_name):
        msg = self.call(make_message("options", name=watcher_name))
        conf = self.configs.get(watcher_name, {})
        conf.update(msg.get('options'))
        self.configs[watcher_name] = conf
        return conf

    def reset(self, watcher_name):
        self.timeline[watcher_name] = []
        self.tries[watcher_name] = 0
        if watcher_name is self.timers:
            timer = self.timers.pop(watcher_name)
            timer.cancel()

    def check(self, watcher_name):
        timeline = self.timelines[watcher_name]
        if watcher_name in self.configs:
            conf = self.configs[watcher_name]
        else:
            conf = self.update_conf(watcher_name)

        tries = self.tries.get(watcher_name, 0)

        if len(timeline) == conf['times']:
            duration = timeline[-1] - timeline[0] - self.check_delay
            if duration <= conf['within']:
                if tries < conf['max_retry']:
                    logger.info("%s: flapping detected: retry in %2ds",
                            watcher_name, conf['retry_in'])

                    self.cast(make_message("stop", name=watcher_name))

                    self.timelines[watcher_name] = []
                    self.tries[watcher_name] = tries + 1

                    def _start():
                        self.cast(make_message("start", name=watcher_name))

                    timer = Timer(conf['retry_in'], _start)
                    timer.start()
                    self.timers[watcher_name] = timer
                else:
                    logger.info("%s: flapping detected: max retry limit",
                            watcher_name)
                    self.timelines[watcher_name] = []
                    self.tries[watcher_name] = 0
                    self.cast(make_message("stop", name=watcher_name))
            else:
                self.timelines[watcher_name] = []
                self.tries[watcher_name] = 0
