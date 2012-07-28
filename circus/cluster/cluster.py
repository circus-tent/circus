import argparse
import os
import sys
import zmq

from circus.client import CircusClient
from circus.config import read_config
from circus.controller import Controller
from circus.util import _setproctitle, DEFAULT_CLUSTER_DEALER
from zmq.eventloop import ioloop
from zmq.utils.jsonapi import jsonmod as json


class ClusterController(Controller):
    def handle_message(self, raw_msg):
        print raw_msg
        node, msg = json.loads(raw_msg[1])
        print node
        print msg
        print self.node_endpoints[node]
        client = CircusClient(endpoint=self.node_endpoints[node])
        response = client.call(msg)
        self.stream.send(raw_msg[0], zmq.SNDMORE)
        self.stream.send(json.dumps(response))


class CircusCluster(object):
    def __init__(self, endpoint=DEFAULT_CLUSTER_DEALER, loop=None,
                 context=None, check_delay=1.):
        self.endpoint = endpoint

        # initialize zmq context
        self.context = context or zmq.Context.instance()
        self.loop = loop or ioloop.IOLoop()
        self.ctrl = ClusterController(endpoint, self.context, self.loop, self,
                check_delay)

    @classmethod
    def load_from_config(cls, config_file):
        if not os.path.exists(config_file):
            sys.stderr.write("the configuration file %r does not exist\n" %
                    config_file)
            sys.stderr.write("Exiting...\n")
            sys.exit(1)

        cfg, cfg_files_read = read_config(config_file)
        dget = cfg.dget
        config = {}

        # main circus options
        config['endpoint'] = dget('circusd-cluster', 'endpoint',
                                  DEFAULT_CLUSTER_DEALER, str)

        return cls(endpoint=config['endpoint'])

    def start(self):
        _setproctitle('circusd-cluster')

        self.ctrl.start()

        while True:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
            else:
                break

    def stop(self):
        self.ctrl.stop()

    def manage_watchers(self):
        pass

    def get_watcher(self, arg):
        print 'get watcher'
        print arg
        return None


def main():
    parser = argparse.ArgumentParser(description='Run some watchers.')
    parser.add_argument('config', help='configuration file', nargs='?')

    args = parser.parse_args()

    cluster = CircusCluster.load_from_config(args.config)
    print cluster.endpoint

    try:
        cluster.start()
    except KeyboardInterrupt:
        pass
    finally:
        cluster.stop()

    sys.exit(0)


if __name__ == '__main__':
    main()
