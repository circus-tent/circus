import sys
import argparse
import os
import logging
import resource
from collections import defaultdict
import zmq
import json
import threading
import Queue
import time

from circus import logger
from circus import util
from circus.consumer import CircusConsumer
from circus.commands import get_commands
from circus.client import CircusClient


class StatWorker(threading.Thread):
    def __init__(self, queue, results, delay=.1):
        threading.Thread.__init__(self)
        self.queue = queue
        self.delay = delay
        self.running = False
        self.results = results
        self.daemon = True

    def run(self):
        self.running = True
        while self.running:
            try:
                pid = self.queue.get(timeout=self.delay)
                try:
                    info = util.get_info(pid, interval=.1)
                except util.NoSuchProcess:
                    # the process is gone !
                    pass
                else:
                    self.results.put(info)
            except Queue.Empty:
                pass
            except Exception, e:
                print str(e)
                raise


class ProcStats(object):
    def __init__(self, stats, pool_size=10):
        self.stats = stats
        self.running = False
        self.pool_size = pool_size
        self.queue = Queue.Queue()
        self.results = Queue.Queue()
        self.workers = [StatWorker(self.queue, self.results)
                        for i in range(self.pool_size)]

    def start(self):
        self.running = True
        for worker in self.workers:
            worker.start()

        while self.running:
            # filling a working queue with all pids
            for pid in self.stats.get_pids():
                self.queue.put(pid)

    def stop(self):
        self.running = False
        for worker in workers:
            worker.stop()


class CircusStats(object):
    def __init__(self, endpoint, pubsub_endoint, pool_size=10):
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
        self.lock = threading.RLock()
        self.stats = ProcStats(self, pool_size)

    def get_pids(self):
        return self._pids

    def _init(self):
        with self.lock:
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

    def remove_pid(self, pid):
        if pid in self._pids:
            with self.lock:
                self._pids.remove(pid)

    def append_pid(self, pid):
        if pid in self._pids:
            return
        with self.lock:
            self._pids.append(pid)

    def start(self):
        self._init()
        print 'initial list is ' + str(self._pids)
        self.running = True
        self.stats.start()

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
                            with self.lock:
                                self._pids.remove(pid)
                        print self._pids
                    elif action == 'spawn':
                        pid = msg['process_pid']
                        if pid not in self._pids:
                            with self.lock:
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
