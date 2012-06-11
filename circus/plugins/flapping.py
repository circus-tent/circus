from threading import Timer
import time

from circus import logger
from circus.plugins import CircusPlugin
from circus.util import to_bool


class Flapping(CircusPlugin):
    """ Plugin that controls the flapping and stops the watcher in case
        it happens too often.

    Plugin Options -- all of them can be overriden in the watcher options
    with a *flapping.* prefix:

    - **attempts** -- number of times a process can restart before we
      start to detect the flapping (default: 2)
    - **window** -- the time window in seconds to test for flapping.
      If the process restarts more than **times** times, we consider it a
      flapping process. (default: 1)
    - **retry_in**: time in seconds to wait until we try to start a process
      that has been flapping. (default: 7)
    - **max_retry**: the number of times we attempt to start a process, before
      we abandon and stop the whole watcher. (default: 5)
    - **active** -- define if the plugin is active or not (default: True).
      If the global flag is set to False, the plugin is not started.

    """
    name = 'flapping'

    def __init__(self, endpoint, pubsub_endpoint, check_delay,
                 **config):
        super(Flapping, self).__init__(endpoint, pubsub_endpoint,
                                       check_delay, **config)
        self.timelines = {}
        self.timers = {}
        self.configs = {}
        self.tries = {}

        # default options
        self.attempts = int(config.get('attempts', 2))
        self.window = float(config.get('window', 1))
        self.retry_in = float(config.get('retry_in', 7))
        self.max_retry = int(config.get('max_retry', 5))

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
        for key, value in msg.get('options', {}).items():
            key = key.split('.')
            if key[0] != self.name:
                continue
            key = '.'.join(key[1:])
            if key in ('attempts', 'max_retry'):
                value = int(value)
            elif key in ('window', 'retry_in'):
                value = float(value)

            conf[key] = value

        self.configs[watcher_name] = conf
        return conf

    def reset(self, watcher_name):
        self.timeline[watcher_name] = []
        self.tries[watcher_name] = 0
        if watcher_name is self.timers:
            timer = self.timers.pop(watcher_name)
            timer.cancel()

    def _get_conf(self, conf, name):
        return conf.get(name, getattr(self, name))

    def check(self, watcher_name):
        timeline = self.timelines[watcher_name]
        if watcher_name in self.configs:
            conf = self.configs[watcher_name]
        else:
            conf = self.update_conf(watcher_name)

        # if the watcher is not activated, we skip it
        if not to_bool(self._get_conf(conf, 'active')):
            # nothing to do here
            return

        tries = self.tries.get(watcher_name, 0)

        if len(timeline) == self._get_conf(conf, 'attempts'):
            duration = timeline[-1] - timeline[0] - self.check_delay

            if duration <= self._get_conf(conf, 'window'):
                if tries < self._get_conf(conf, 'max_retry'):
                    logger.info("%s: flapping detected: retry in %2ds",
                            watcher_name, self._get_conf(conf, 'retry_in'))

                    self.cast("stop", name=watcher_name)
                    self.timelines[watcher_name] = []
                    self.tries[watcher_name] = tries + 1

                    def _start():
                        self.cast("start", name=watcher_name)

                    timer = Timer(self._get_conf(conf, 'retry_in'), _start)
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
