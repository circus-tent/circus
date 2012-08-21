import argparse
import os
import sys
import zmq

from circus.client import CircusClient
from circus.commands import errors, get_commands
from circus.commands.base import ok, error
from circus.config import get_config
from circus.consumer import CircusConsumer
from circus.controller import Controller
from circus.exc import CallError
from circus.util import _setproctitle, DEFAULT_CLUSTER_DEALER, DEFAULT_CLUSTER_STATS
from threading import Lock, Thread
from zmq.eventloop import ioloop
from zmq.utils.jsonapi import jsonmod as json


class ClusterController(Controller):
    def handle_node(self, nodes, ssh_server, node, response, response_lock, cluster_timeout, cmd, lock):
        client = CircusClient(endpoint=nodes[node]['endpoint'], timeout=cluster_timeout, ssh_server=ssh_server)
        try:
            resp = client.call(cmd)
        except CallError as e:
            resp = {'err': str(e) + " Try to raise the --timeout value"}
        resp['node'] = node
        response_lock.acquire()
        response.append(resp)
        response_lock.release()
        lock.release()

    def handle_message(self, raw_msg):
        cid, msg = raw_msg[0], json.loads(raw_msg[1])
        try:
            cmd = msg['cmd']
            broadcast = msg['broadcast']
            cluster_timeout = msg['cluster_timeout']
            node_name = msg['node']
        except KeyError as e:
            self.send_error(cid, msg, reason="message has no '" + e.message + "' field", errno=errors.MESSAGE_ERROR)
            return
        print cmd
        if cmd.get('command') == 'nodelist':
            response = ok(self.commands['nodelist'].execute(self.arbiter, cmd.get('properties', {})))
        elif cmd.get('command') == 'register_node':
            result = self.commands['register_node'].execute(self.arbiter, cmd.get('properties', {}))
            if result['success']:
                response = ok(result)
            else:
                response = error(reason="node name '" + result['node_name'] + "' is already registered")
        else:
            response = []
            response_lock = Lock()
            locks = []
            for node in self.arbiter.nodes:
                if node == node_name or broadcast:
                    lock = Lock()
                    lock.acquire()
                    locks.append(lock)
                    Thread(target=self.handle_node,
                           args=(self.arbiter.nodes, self.arbiter.ssh_server,
                                 node, response, response_lock,
                                 cluster_timeout, cmd, lock)).start()
            for lock in locks:
                lock.acquire()
            if len(response) == 1 and not broadcast:
                response = response[0]
            elif len(response) == 0:
                response = {'err': 'No matching node'}
        self.send_response(cid, msg, response)

    def start(self):
        if self.arbiter.stats_endpoint is not None:
            self.stats_forwarder = StatsForwarder(self.arbiter.nodes, cluster_stats_endpoint=self.arbiter.stats_endpoint)
            self.stats_forwarder.start()
        super(ClusterController, self).start()

    def stop_stats_forwarder(self):
        if hasattr(self, 'stats_forwarder'):
            self.stats_forwarder.stop()


class CircusCluster(object):
    def __init__(self, nodes, endpoint=DEFAULT_CLUSTER_DEALER, stats_endpoint=None, loop=None,
                 context=None, check_delay=1., ssh_server=None):
        self.nodes = {}
        for node in nodes:
            self.nodes[node['name']] = {}
            for key in node:
                if not key == 'name':
                    self.nodes[node['name']][key] = node[key]
        self.endpoint = endpoint
        self.stats_endpoint = stats_endpoint
        self.ssh_server = ssh_server

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

        config = get_config(config_file)
        # XXX ssh server requires changes in branch issue233
        return cls(config['nodes'], endpoint=config['cluster']['endpoint'],
                   stats_endpoint=config['cluster'].get('stats_endpoint', None),
                   ssh_server=config['cluster'].get('ssh_server', None))

    def start(self):
        _setproctitle('circusd-cluster')
        
        # XXX need to start the beat for each node since register_node is skipped

        cmd = get_commands()['join_cluster']
        def execute_join_cluster(node_name, node_endpoint, master_endpoint):
            msg = cmd.message(node_name, master_endpoint)
            CircusClient(endpoint=node_endpoint, ssh_server=self.ssh_server).call(msg)
            
        for node in self.nodes:
            Thread(target=execute_join_cluster,
                   args=(node, self.nodes[node]['endpoint'], self.endpoint)).start()

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
        print 'stopping'
        self.ctrl.stop_stats_forwarder()
        #self.ctrl.stop()

    def manage_watchers(self):
        pass

    def get_watcher(self, arg):
        print 'get watcher'
        print arg
        return None


class StatsForwarder(Thread):
    def __init__(self, nodes, cluster_stats_endpoint=DEFAULT_CLUSTER_STATS):
        super(StatsForwarder, self).__init__()
        self.nodes = nodes
        self.cluster_stats_endpoint = cluster_stats_endpoint

    def run(self):
        context = zmq.Context()
        sender = context.socket(zmq.PUB)
        sender.bind(self.cluster_stats_endpoint)

        self.consumer = CircusConsumer(['stat.'], endpoint=None)

        for node in self.nodes:
            self.add_connection(self.nodes[node].get('stats_endpoint', None))

        for topic, msg in self.consumer:
            stat = json.loads(msg)
            if 'node_name' in stat:
                topic = topic.split('.')
                topic[1] = stat['node_name'] + '-' + topic[1]
                topic = '.'.join(topic)
                sender.send_multipart([topic, msg])

    def stop(self):
        self.consumer.stop()

    def add_connection(self, stats_endpoint):
        self.consumer.add_connection(stats_endpoint)


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
