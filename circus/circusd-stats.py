import sys
import argparse
import os
import logging
import resource
from collections import defaultdict
import zmq
import json

from circus import logger
from circus import util
from circus.consumer import CircusConsumer
from circus.commands import get_commands
from circus.client import CircusClient


class CircusStats(object):
    def __init__(self, endpoint, pubsub_endoint):
        self.topic = 'watcher.'
        self.ctx = zmq.Context()
        self.consumer = CircusConsumer([self.topic], context=self.ctx,
                                       endpoint=pubsub_endoint)
        self.client = CircusClient(context=self.ctx, endpoint=endpoint)
        self.cmds = get_commands()
        self.watchers = defaultdict(list)
        self._pids = []
        self.running = False
        self.stopped = False

    def _init(self):
        self.stopped = False
        self._pids = []
        # getting the initial list of watchers/pids
        msg = self.cmds['list'].make_message()
        res = self.client.call(msg)
        for watcher in res['watchers']:
            msg = self.cmds['listpids'].make_message(name=watcher)
            res = self.client.call(msg)
            for pid in res['pids']:
                if pid in self._pids:
                    continue
                self._pids.append(pid)

    def start(self):
        self._init()
        print 'initial list is ' + str(self._pids)
        self.running = True
        while self.running:
            # now hooked into the stream
            try:
                for topic, msg in self.consumer:
                    __, name, action = topic.split('.')
                    msg = json.loads(msg)
                    if action != 'start' and self.stopped:
                        self._init()

                    if action in ('reap', 'kill'):
                        # a process was reaped
                        pid = msg['process_pid']
                        if pid in self._pids:
                            self._pids.remove(pid)
                        print self._pids
                    elif action == 'spawn':
                        pid = msg['process_pid']
                        if pid not in self._pids:
                            self._pids.append(pid)
                        print self._pids
                    elif action == 'start':
                        self._init()
                        print self._pids
                    elif action == 'stop':
                        # nothing to do
                        self.stopped = True
                    else:
                        print action
                        print msg

            except Exception, e:
                print str(e)

    def stop(self):
        self.running = False
        self.ctx.destroy(0)

def main():
    parser = argparse.ArgumentParser(description=
                                     'Runs the stats aggregator for Circus')

    parser.add_argument('--endpoint',
            help='The ZeroMQ pub/sub socket to connect to',
            default='tcp://127.0.0.1:5555')


    parser.add_argument('--pubsub',
            help='The ZeroMQ pub/sub socket to connect to',
            default='tcp://127.0.0.1:5556')

    args = parser.parse_args()
    stats = CircusStats(args.endpoint, args.pubsub)

    try:
        stats.start()
    finally:
        stats.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
