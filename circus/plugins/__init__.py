""" Base class to create Circus subscribers plugins.
"""
import sys
import errno
import uuid
import argparse

import zmq
import zmq.utils.jsonapi as json
from tornado import ioloop
from zmq.eventloop import zmqstream

from circus import logger, __version__
from circus.client import make_message, cast_message
from circus.util import (debuglog, to_bool, resolve_name, configure_logger,
                         DEFAULT_ENDPOINT_DEALER, DEFAULT_ENDPOINT_SUB,
                         get_connection, to_str, to_bytes)


class CircusPlugin(object):
    """Base class to write plugins.

    Options:

    - **context** -- the ZMQ context to use
    - **endpoint** -- the circusd ZMQ endpoint
    - **pubsub_endpoint** -- the circusd ZMQ pub/sub endpoint
    - **check_delay** -- the configured check delay
    - **config** -- free config mapping
    """
    name = ''

    def __init__(self, endpoint, pubsub_endpoint, check_delay, ssh_server=None,
                 **config):
        self.daemon = True
        self.config = config
        self.active = to_bool(config.get('active', True))
        self.pubsub_endpoint = pubsub_endpoint
        self.endpoint = endpoint
        self.check_delay = check_delay
        self.ssh_server = ssh_server
        self._id = to_bytes(uuid.uuid4().hex)
        self.running = False
        self.loop = ioloop.IOLoop()

    @debuglog
    def initialize(self):
        self.context = zmq.Context()
        self.client = self.context.socket(zmq.DEALER)
        self.client.setsockopt(zmq.IDENTITY, self._id)
        get_connection(self.client, self.endpoint, self.ssh_server)
        self.client.linger = 0
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b'watcher.')
        self.sub_socket.connect(self.pubsub_endpoint)
        self.substream = zmqstream.ZMQStream(self.sub_socket, self.loop)
        self.substream.on_recv(self.handle_recv)

    @debuglog
    def start(self):
        self.loop.make_current()
        if not self.active:
            raise ValueError('Will not start an inactive plugin')
        self.handle_init()
        self.initialize()
        self.running = True

        while True:
            try:
                self.loop.start()
            except zmq.ZMQError as e:
                logger.debug(str(e))

                if e.errno == errno.EINTR:
                    continue
                elif e.errno == zmq.ETERM:
                    break
                else:
                    logger.debug("got an unexpected error %s (%s)", str(e),
                                 e.errno)
                    raise
            else:
                break

        self.substream.close()
        self.client.close()
        self.sub_socket.close()
        self.context.destroy()

    @debuglog
    def stop(self):
        if not self.running:
            self.loop.close()
            return

        try:
            self.handle_stop()
        finally:
            self.loop.stop()

        self.running = False

    def call(self, command, **props):
        """Sends the command to **circusd**

        Options:

        - **command** -- the command to call
        - **props** -- keyword arguments to add to the call

        Returns the JSON mapping sent back by **circusd**
        """
        msg = make_message(command, **props)
        self.client.send(json.dumps(msg))
        msg = self.client.recv()
        return json.loads(msg)

    def cast(self, command, **props):
        """Fire-and-forget a command to **circusd**

        Options:

        - **command** -- the command to call
        - **props** -- keyword arguments to add to the call
        """
        msg = cast_message(command, **props)
        self.client.send(json.dumps(msg))

    #
    # methods to override.
    #
    def handle_recv(self, data):
        """Receives every event published by **circusd**

        Options:

        - **data** -- a tuple containing the topic and the message.
        """
        raise NotImplementedError()

    def handle_stop(self):
        """Called right before the plugin is stopped by Circus.
        """
        pass

    def handle_init(self):
        """Called right before a plugin is started - in the thread context.
        """
        pass

    @staticmethod
    def split_data(data):
        topic, msg = data
        topic_parts = to_str(topic).split(".")
        return topic_parts[1], topic_parts[2], msg

    @staticmethod
    def load_message(msg):
        return json.loads(msg)


def _cfg2str(cfg):
    return ':::'.join([
         '%s:%s' % (key, val) for key, val in sorted(cfg.items())
    ])


def _str2cfg(data):
    cfg = {}
    if data is None:
        return cfg

    for item in data.split(':::'):
        item = item.split(':', 1)
        if len(item) != 2:
            continue
        key, value = item
        cfg[key.strip()] = value.strip()

    return cfg


def get_plugin_cmd(config, endpoint, pubsub, check_delay, ssh_server,
                   debug=False, loglevel=None, logoutput=None):
    fqn = config['use']
    # makes sure the name exists
    resolve_name(fqn)

    # we're good, serializing the config
    del config['use']
    config = _cfg2str(config)
    cmd = "%s -c 'from circus import plugins;plugins.main()'" % sys.executable
    cmd += ' --endpoint %s' % endpoint
    cmd += ' --pubsub %s' % pubsub
    if ssh_server is not None:
        cmd += ' --ssh %s' % ssh_server
    if len(config) > 0:
        cmd += ' --config %s' % config
    if debug:
        cmd += ' --log-level DEBUG'
    elif loglevel:
        cmd += ' --log-level ' + loglevel
    if logoutput:
        cmd += ' --log-output ' + logoutput
    cmd += ' %s' % fqn
    return cmd


def main():
    parser = argparse.ArgumentParser(description='Runs a plugin.')

    parser.add_argument('--endpoint',
                        help='The circusd ZeroMQ socket to connect to',
                        default=DEFAULT_ENDPOINT_DEALER)

    parser.add_argument('--pubsub',
                        help='The circusd ZeroMQ pub/sub socket to connect to',
                        default=DEFAULT_ENDPOINT_SUB)

    parser.add_argument('--config', help='The plugin configuration',
                        default=None)

    parser.add_argument('--version', action='store_true', default=False,
                        help='Displays Circus version and exits.')

    parser.add_argument('--check-delay', type=float, default=5.,
                        help='Checck delay.')

    parser.add_argument('plugin',
                        help='Fully qualified name of the plugin class.',
                        nargs='?')

    parser.add_argument('--log-level', dest='loglevel', default='info',
                        help="log level")

    parser.add_argument('--log-output', dest='logoutput', default='-',
                        help="log output")

    parser.add_argument('--ssh', default=None, help='SSH Server')

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    if args.plugin is None:
        parser.print_usage()
        sys.exit(0)

    factory = resolve_name(args.plugin)

    # configure the logger
    configure_logger(logger, args.loglevel, args.logoutput, name=factory.name)

    # load the plugin and run it.
    logger.info('Loading the plugin...')
    logger.info('Endpoint: %r' % args.endpoint)
    logger.info('Pub/sub: %r' % args.pubsub)
    plugin = factory(args.endpoint, args.pubsub,
                     args.check_delay, args.ssh,
                     **_str2cfg(args.config))
    logger.info('Starting')
    try:
        plugin.start()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info('Stopping')
        plugin.stop()
    sys.exit(0)


if __name__ == '__main__':
    main()
