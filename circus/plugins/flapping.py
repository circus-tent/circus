from threading import Timer
import time

from circus import logger
from circus.plugins import CircusPlugin


class Flapping(CircusPlugin):
    """ Plugin that controls the flapping and acts upon.
    """
    name = 'flapping'

    def __init__(self, context, endpoint, pubsub_endpoint, check_delay):
        super(Flapping, self).__init__(context, endpoint, pubsub_endpoint,
                                       check_delay)
        self.timelines = {}
        self.timers = {}
        self.configs = {}
        self.tries = {}

    def handle_stop(self):
        for _, timer in self.timers.items():
            timer.cancel()

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

    def update_conf(self, watcher_name):
        msg = self.call("options", name=watcher_name)
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

        # if the watcher is not activated, we skip it
        if not conf['check_flapping']:
            # nothing to do here
            return

        tries = self.tries.get(watcher_name, 0)

        if len(timeline) == conf['flapping_attempts']:
            duration = timeline[-1] - timeline[0] - self.check_delay
            if duration <= conf['flapping_window']:
                if tries < conf['max_retry']:
                    logger.info("%s: flapping detected: retry in %2ds",
                            watcher_name, conf['retry_in'])

                    self.cast("stop", name=watcher_name)

                    self.timelines[watcher_name] = []
                    self.tries[watcher_name] = tries + 1

                    def _start():
                        self.cast("start", name=watcher_name)

                    timer = Timer(conf['retry_in'], _start)
                    timer.start()
                    self.timers[watcher_name] = timer
                else:
                    logger.info("%s: flapping detected: max retry limit",
                            watcher_name)
                    self.timelines[watcher_name] = []
                    self.tries[watcher_name] = 0
                    self.cast("stop", name=watcher_name)
            else:
                self.timelines[watcher_name] = []
                self.tries[watcher_name] = 0
