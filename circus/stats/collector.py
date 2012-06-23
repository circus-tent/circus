import socket
from collections import defaultdict
from threading import Thread
import time

from circus import util
from circus import logger

from zmq.eventloop import ioloop
from iowait import IOWait



class BaseStatsCollector(ioloop.PeriodicCallback):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        ioloop.PeriodicCallback.__init__(self, self._callback,
                                         callback_time * 1000, io_loop)
        self.streamer = streamer
        self.name = name

    def _callback(self):
        logger.debug('Publishing stats about {0}'.format(self.name))
        for stats in self.collect_stats():
            self.streamer.publisher.publish(self.name, stats)

    def collect_stats(self):
        # should be implemented in subclasses
        raise NotImplementedError()


class WatcherStatsCollector(BaseStatsCollector):
    def _aggregate(self, aggregate):
        res = {'pid': aggregate.keys()}
        stats = aggregate.values()

        # aggregating CPU does not mean anything
        # but the average can be a good indicator
        cpu = [stat['cpu'] for stat in stats]
        if 'N/A' in cpu:
            res['cpu'] = 'N/A'
        else:
            try:
                res['cpu'] = sum(cpu) / len(cpu)
            except ZeroDivisionError:
                res['cpu'] = 0.

        # aggregating memory does make sense
        mem = [stat['mem'] for stat in stats]
        if 'N/A' in mem:
            res['mem'] = 'N/A'
        else:
            res['mem'] = sum(mem)
        return res

    def collect_stats(self):
        aggregate = {}

        # sending by pids
        for pid in self.streamer.get_pids(self.name):
            name = None

            if self.name == 'circus':
                if pid in self.streamer.circus_pids:
                    name = self.streamer.circus_pids[pid]

            try:
                info = util.get_info(pid)
                aggregate[pid] = info
                info['subtopic'] = pid
                info['name'] = name
                yield info
            except util.NoSuchProcess:
                # the process is gone !
                pass
            except Exception, e:
                logger.exception('Failed to get info for %d. %s' % (pid,
                    str(e)))

        # now sending the aggregation
        yield self._aggregate(aggregate)



class SocketStatsCollector(BaseStatsCollector):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        super(SocketStatsCollector, self).__init__(streamer, name,
                callback_time, io_loop)
        # if gevent is installed, we'll use a greenlet,
        # otherwise we'll use a thread
        try:
            import gevent       # NOQA
            self.greenlet = True
            self._init_greenlet()
        except ImportError:
            self.greenlet = False
            self._init_thread()

        self.running = False
        self._rstats = defaultdict(int)

    def _init_greenlet(self):
        from gevent import Greenlet
        self._runner = Greenlet(self._select)

    def _init_thread(self):
        self._runner = Thread(target=self._select)

    def start(self):
        # starting the thread or greenlet
        self.running = True
        self._runner.start()
        super(SocketStatsCollector, self).start()

    def stop(self):
        # stopping the thread or greenlet
        self.running = False
        self._runner.join()
        BaseStatsCollector.stop(self)

    def _select(self):
        # collecting hits continuously
        poller = IOWait()
        fds = {}

        for sock, address in self.streamer.get_sockets():
            poller.watch(sock, read=True, write=False)

        while self.running:
            # polling for events
            events = poller.wait(self.callback_time)

            if len(events) == 0:
                continue

            for socket, read, write in events:
                if read:
                    self._rstats[socket.fileno()] += 1

            time.sleep(.001)      # maximum resolution 1 ms

    def _aggregate(self, aggregate):
        raise NotImplementedError()

    def collect_stats(self):
        # sending hits by sockets
        sockets = self.streamer.get_sockets()
        fds = [(address, sock.fileno()) for sock, address in sockets]

        total = {'addresses': [], 'reads': 0}
        # we might lose a few hits here but it's ok
        for address, fd in fds:
            info = {}
            info['fd'] = info['subtopic'] = fd
            info['reads'] = self._rstats[fd]
            total['reads'] += info['reads']
            total['addresses'].append(address)
            info['address'] = address
            self._rstats[fd] = 0
            yield info

        yield total
