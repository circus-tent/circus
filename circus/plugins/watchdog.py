"""WatchDog plugin

One process to watch several other processes

2 methods:
- uses of zmqueue to make a heartbeat between the processes
  (see: https://github.com/mozilla-services/loads/blob/master/loads/transport/heartbeat.py)
- bind on a udp socket and wait for watchdog messages

Each watchdog message should have:
    * the pid of the process generating the watchdog (used for identifying the
      process in circus processes list)
    * a timestamp ?

"""

import socket
from zmq.eventloop import ioloop
from circus.plugins import CircusPlugin


class WatchDog(CircusPlugin):
    """Plugin that sends stuff to statsd
    """
    name = 'watchdog'
    default_app_name = "app"

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server,
                 **config):
        super(WatchDog, self).__init__(endpoint, pubsub_endpoint,
                                       check_delay, ssh_server=ssh_server)
        self.app = config.get('application_name', self.default_app_name)

        # initialize statsd
        self.statsd = StatsdClient(host=config.get('host', 'localhost'),
                                   port=int(config.get('port', '8125')),
                                   prefix=self.prefix,
                                   sample_rate=float(
                                       config.get('sample_rate', '1.0')))
