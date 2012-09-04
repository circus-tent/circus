from circus.plugins import CircusPlugin
from zmq.eventloop import ioloop


try:
    import statsd
except ImportError:
    raise ImportError("This plugin needs the statsd-client lib.")


class StatsdClient(statsd.StatsdClient):
    def decrement(self, *args, **kwargs):
        return self.decr(*args, **kwargs)

    def increment(self, *args, **kwargs):
        return self.incr(*args, **kwargs)

    def gauge(self, bucket, value):
        self._send(bucket, str(value).encode("utf-8") + b'|g', sample_rate=1)


class StatsdEmitter(CircusPlugin):
    """Plugin that sends stuff to statsd
    """
    name = 'statsd'

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server,
                 **config):
        super(StatsdEmitter, self).__init__(endpoint, pubsub_endpoint,
                                            check_delay, ssh_server=ssh_server)
        self.app = config.get('application_name', 'app')
        self.prefix = 'circus.%s.watcher' % self.app

        # initialize statsd
        self.statsd = StatsdClient(host=config.get('host', 'localhost'),
                port=int(config.get('port', '8125')), prefix=self.prefix,
                sample_rate=float(config.get('sample_rate', '1.0')))

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = topic.split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        self.statsd.increment('%s.%s' % (watcher, action))


class FullStats(StatsdEmitter):

    name = 'full_stats'

    def __init__(self, *args, **config):
        super(FullStats, self).__init__(*args, **config)
        self.loop_rate = config.get("loop_rate", 5)

        if not bool(config.get("no_circus_stats", True)):
            # do ignore receive calls
            self.handle_recv = lambda x: x

    def handle_init(self):
        self.period = ioloop.PeriodicCallback(self.request_stats, self.loop_rate * 1000, self.loop)
        self.period.start()

    def request_stats(self):
        info = self.call("stats")
        if info["status"] == "error":
            self.statsd.increment("_stats.error")
            return

        for name, stats in info['info']:
            print name, stats

    def handle_stop(self):
        self.period.start()


class RedisStats(FullStats):

    name = 'redis_stats'

    OBSERVE = ['pubsub_channels', 'connected_slaves', 'lru_clock',
                'connected_clients', 'keyspace_misses', 'used_memory',
                'used_memory_peak', 'total_commands_processed',
                'used_memory_rss', 'total_connections_received',
                'pubsub_patterns', 'used_cpu_sys', 'used_cpu_sys_children',
                'blocked_clients', 'used_cpu_user', 'client_biggest_input_buf',
                'mem_fragmentation_ratio', 'expired_keys', 'evicted_keys',
                'client_longest_output_list', 'uptime_in_seconds', 'keyspace_hits']

    # do nothing on receive events
    handle_recv = lambda s, x: x

    def __init__(self, *args, **config):
        super(RedisStats, self).__init__(*args, **config)
        import redis
        self.redis = redis.from_url(config.get("redis_url", "redis://localhost:6379/0"),
                float(config.get("timeout", 1)))

    def request_stats(self):
        try:
            info = self.redis.info()
        except Exception:
            self.statsd.increment("redis_stats.error")
            return

        for key in self.OBSERVE:
            self.statsd.gauge("redis_stats.%s" % key, info[key])
