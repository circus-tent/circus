from circus.plugins import CircusPlugin
from zmq.eventloop import ioloop

import socket


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
            value += b"|@" + sample_rate

        if self.prefix:
            bucket = "%s.%s" % (self.prefix, bucket)

        self.socket.sendto("%s:%s" % (bucket, value), (self.host, self.port))

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
        topic, msg = data
        topic_parts = topic.split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        self.statsd.increment('%s.%s' % (watcher, action))


class BaseObserver(StatsdEmitter):

    def __init__(self, *args, **config):
        super(BaseObserver, self).__init__(*args, **config)
        self.loop_rate = config.get("loop_rate", 60)  # in seconds

    def handle_init(self):
        self.period = ioloop.PeriodicCallback(self.look_after,
                                              self.loop_rate * 1000, self.loop)
        self.period.start()

    def handle_stop(self):
        self.period.stop()

    def handle_recv(self, data):
        pass

    def look_after(self):
        raise NotImplemented


class FullStats(BaseObserver):

    name = 'full_stats'

    def look_after(self):
        info = self.call("stats")
        if info["status"] == "error":
            self.statsd.increment("_stats.error")
            return

        for name, stats in info['infos'].iteritems():
            if name.startswith("plugin:"):
                # ignore plugins
                continue

            cpus = []
            mems = []

            for sub_info in stats.itervalues():
                if isinstance(sub_info,  basestring):
                    # dead processes have a string instead of actual info
                    # ignore that
                    continue
                cpus.append(sub_info['cpu'])
                mems.append(sub_info['mem'])

            self.statsd.gauge("_stats.%s.watchers_num" % name, len(cpus))

            if not cpus:
                # if there are only dead processes, we have an empty list
                # and we can't measure it
                continue
            self.statsd.gauge("_stats.%s.cpu_max" % name, max(cpus))
            self.statsd.gauge("_stats.%s.cpu_sum" % name, sum(cpus))
            self.statsd.gauge("_stats.%s.mem_max" % name, max(mems))
            self.statsd.gauge("_stats.%s.mem_sum" % name, sum(mems))
