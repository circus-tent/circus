import errno
import json
from threading import Thread, Timer
import time
import uuid

import zmq
from zmq.eventloop import ioloop, zmqstream

from circus import logger


class Flapping(Thread):

    def __init__(self, endpoint, pubsub_endpoint, check_delay):
        super(Flapping, self).__init__()
        self.daemon = True

        self.check_delay = check_delay
        self.context = zmq.Context()
        self.loop = ioloop.IOLoop()
        self._id = uuid.uuid4().hex
        self.timelines = {}
        self.timers = {}
        self.configs = {}
        self.tries = {}

        self.pubsub_endpoint = pubsub_endpoint
        self.endpoint = endpoint
        self.alive = True
        self.initialize()

    def initialize(self):
        self.client = self.context.socket(zmq.DEALER)
        self.client.setsockopt(zmq.IDENTITY, self._id)
        self.client.connect(self.endpoint)

        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b'show.')
        self.sub_socket.connect(self.pubsub_endpoint)

        self.substream = zmqstream.ZMQStream(self.sub_socket, self.loop)
        self.substream.on_recv(self.handle_recv)

    def run(self):
        while self.alive:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
            else:
                break

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = topic.split(".")
        if topic_parts[2] == "reap":
            json_obj = json.loads(msg)
            timeline = self.timelines.get(topic_parts[1], [])
            timeline.append(time.time())
            self.timelines[topic_parts[1]] = timeline

            self.check(topic_parts[1])
        elif topic_parts[2] == "updated":
            self.update_conf(topic_parts[1])


    def call(self, cmd):
        self.client.send(cmd)
        msg = self.client.recv()
        return msg

    def update_conf(self, show_name):
        options_str = self.call("options %s" % show_name)
        conf = self.configs.get(show_name, {})
        for line in options_str.split("\n"):
            k, v = line.split(":", 1)
            k1 = k.strip()

            if k1 == "times":
                conf[k1]  = int(v.strip())
            elif k1 == "within":
                conf[k1]  = float(v.strip())
            elif k1 == "retry_in":
                conf[k1]  = float(v.strip())
            elif k1 == "max_retry":
                conf[k1] = int(v.strip())

        self.configs[show_name] = conf
        return conf


    def stop(self):
        self.alive = False
        for _, timer in self.timers.items():
            timer.cancel()
        self.loop.stop()
        time.sleep(0.1)
        self.context.destroy(0)
        self.join()

    def reset(self, show_name):
        self.timeline[show_name] = []
        self.tries[show_name] = 0
        if show_name is self.timers:
            timer = self.timers.pop(show_name)
            timer.cancel()

    def check(self, show_name):
        timeline = self.timelines[show_name]
        if show_name in self.configs:
            conf = self.configs[show_name]
        else:
            conf = self.update_conf(show_name)

        tries = self.tries.get(show_name, 0)

        if len(timeline) == conf['times']:
            duration = timeline[-1] - timeline[0] - self.check_delay
            if duration <= conf['within']:
                if tries < conf['max_retry']:
                    logger.info("%s: flapping detected: retry in %2ds" %
                            (show_name, conf['retry_in']))

                    self.call("stop_show %s" % show_name)

                    self.timelines[show_name] = []
                    self.tries[show_name] = tries + 1

                    def _start():
                        self.call("start_show %s" % show_name)

                    timer = Timer(conf['retry_in'], _start)
                    timer.start()
                    self.timers[show_name] = timer
                else:
                    logger.info("%s: flapping detected: max retry limit" %
                            show_name)
                    self.timelines[show_name] = []
                    self.tries[show_name] = 0
                    self.client.send("stop %s" % show_name)
            else:
                self.timelines[show_name] = []
                self.tries[show_name] = 0
