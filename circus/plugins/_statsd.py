from circus.plugins import CircusPlugin

try:
    import statsd
except ImportError:
    raise ImportError("This plugin needs the statsd-client lib.")


class StatsdEmitter(CircusPlugin):
    """Plugin that sends stuff to statsd
    """
    name = 'statsd'

    def __init__(self, endpoint, pubsub_endpoint, check_delay,
                 **config):
        super(StatsdEmitter, self).__init__(endpoint, pubsub_endpoint,
                                            check_delay)
        self.app = config.get('application_name', 'app')
        self.prefix = 'circus.%s.watcher' % self.app

        # initialize statsd
        statsd.init_statsd({'STATSD_HOST': config.get('host', 'localhost'),
                            'STATSD_PORT': int(config.get('port', '8125')),
                            'STATSD_SAMPLE_RATE':
                                    float(config.get('sample_rate', '1.0')),
                            'STATSD_BUCKET_PREFIX': self.prefix})

    def handle_recv(self, data):
        topic, msg = data
        topic_parts = topic.split(".")
        watcher = topic_parts[1]
        action = topic_parts[2]
        statsd.increment('%s.%s' % (watcher, action))
