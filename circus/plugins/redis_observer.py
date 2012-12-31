
from circus.plugins.statsd import BaseObserver

try:
    import redis
except ImportError:
    raise ImportError("This plugin requires the redis-lib to run.")


class RedisObserver(BaseObserver):

    name = 'redis_observer'
    default_app_name = "redis_observer"

    OBSERVE = ['pubsub_channels', 'connected_slaves', 'lru_clock',
               'connected_clients', 'keyspace_misses', 'used_memory',
               'used_memory_peak', 'total_commands_processed',
               'used_memory_rss', 'total_connections_received',
               'pubsub_patterns', 'used_cpu_sys', 'used_cpu_sys_children',
               'blocked_clients', 'used_cpu_user', 'client_biggest_input_buf',
               'mem_fragmentation_ratio', 'expired_keys', 'evicted_keys',
               'client_longest_output_list', 'uptime_in_seconds',
               'keyspace_hits']

    def __init__(self, *args, **config):
        super(RedisObserver, self).__init__(*args, **config)
        self.redis = redis.from_url(config.get("redis_url",
                                    "redis://localhost:6379/0"),
                                    float(config.get("timeout", 5)))

        self.restart_on_timeout = config.get("restart_on_timeout", None)

    def look_after(self):
        try:
            info = self.redis.info()
        except redis.ConnectionError:
            self.statsd.increment("redis_stats.error")
            if self.restart_on_timeout:
                self.cast("restart", name=self.restart_on_timeout)
                self.statsd.increment("redis_stats.restart_on_error")
            return

        for key in self.OBSERVE:
            self.statsd.gauge("redis_stats.%s" % key, info[key])
