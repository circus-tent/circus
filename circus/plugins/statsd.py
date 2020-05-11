import socket

from tornado import ioloop

from circus.plugins import CircusPlugin
from circus.util import human2bytes


class StatsdClient(object):

    def __init__(self, host=None, port=None, prefix=None, sample_rate=1):
        self.host = host
        self.port = port
        self.prefix = prefix
        self.sample_rate = sample_rate
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, bucket, value, sample_rate=None):
        sample_rate = sample_rate or self.sample_rate
        if sample_rate != 1:
            value += "|@%s" % sample_rate

        if self.prefix:
            bucket = "%s.%s" % (self.prefix, bucket)

        msg = "%s:%s" % (bucket, value)
        self.socket.sendto(msg.encode('utf-8'), (self.host, self.port))

    def decrement(self, bucket, delta=1):
        if delta > 0:
            delta = - delta
        self.increment(bucket, delta)

    def increment(self, bucket, delta=1):
        self.send(bucket, "%d|c" % delta)

    def gauge(self, bucket, value):
        self.send(bucket, "%s|g" % value)

    def timed(self, bucket, value):
        self.send(bucket, "%s|ms" % value)

    def stop(self):
        self.socket.close()


class StatsdEmitter(CircusPlugin):
    """Plugin that sends stuff to statsd
    """
    name = 'statsd'
    default_app_name = "app"

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server,
                 **config):
        super(StatsdEmitter, self).__init__(endpoint, pubsub_endpoint,
                                            check_delay, ssh_server=ssh_server)
        self.app = config.get('application_name', self.default_app_name)
        self.prefix = 'circus.%s.watcher' % self.app

        # initialize statsd
        self.statsd = StatsdClient(host=config.get('host', 'localhost'),
                                   port=int(config.get('port', '8125')),
                                   prefix=self.prefix,
                                   sample_rate=float(
                                       config.get('sample_rate', '1.0')))

    def handle_recv(self, data):
        watcher_name, action, msg = self.split_data(data)
        self.statsd.increment('%s.%s' % (watcher_name, action))

    def stop(self):
        self.statsd.stop()
        super(StatsdEmitter, self).stop()


class BaseObserver(StatsdEmitter):

    def __init__(self, *args, **config):
        super(BaseObserver, self).__init__(*args, **config)
        self.loop_rate = float(config.get("loop_rate", 60))  # in seconds

    def handle_init(self):
        self.period = ioloop.PeriodicCallback(self.look_after,
                                              self.loop_rate * 1000)
        self.period.start()

    def handle_stop(self):
        self.period.stop()
        self.statsd.stop()

    def handle_recv(self, data):
        pass

    def look_after(self):
        raise NotImplementedError()


class FullStats(BaseObserver):

    name = 'full_stats'

    def look_after(self):
        info = self.call("stats")
        if info["status"] == "error":
            self.statsd.increment("_stats.error")
            return

        for name, stats in info['infos'].items():
            if name.startswith("plugin:"):
                # ignore plugins
                continue

            cpus = []
            mems = []
            mem_infos = []

            for sub_name, sub_info in stats.items():
                if isinstance(sub_info, dict):
                    cpus.append(sub_info['cpu'])
                    mems.append(sub_info['mem'])
                    mem_infos.append(human2bytes(sub_info['mem_info1']))
                elif sub_name == "spawn_count":
                    # spawn_count info is in the same level as processes
                    # dict infos, so if spawn_count is given, take it and
                    # continue
                    self.statsd.gauge("_stats.%s.spawn_count" % name,
                                      sub_info)

            self.statsd.gauge("_stats.%s.watchers_num" % name, len(cpus))

            if not cpus:
                # if there are only dead processes, we have an empty list
                # and we can't measure it
                continue

            self.statsd.gauge("_stats.%s.cpu_max" % name, max(cpus))
            self.statsd.gauge("_stats.%s.cpu_sum" % name, sum(cpus))
            self.statsd.gauge("_stats.%s.mem_pct_max" % name, max(mems))
            self.statsd.gauge("_stats.%s.mem_pct_sum" % name, sum(mems))
            self.statsd.gauge("_stats.%s.mem_max" % name, max(mem_infos))
            self.statsd.gauge("_stats.%s.mem_sum" % name, sum(mem_infos))
