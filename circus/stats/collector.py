import socket
import select
from collections import defaultdict
from threading import Thread

from circus import util
from circus import logger

from zmq.eventloop import ioloop


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
        super(SocketStatsCollector, self).__init__(streamer, name, callback_time,
                                    io_loop)
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
        self._wstats = defaultdict(int)
        self._xstats = defaultdict(int)

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
        while self.running:
            sockets = self.streamer.get_sockets()

            try:
                rlist, wlist, xlist = select.select(sockets, sockets, sockets,
                                                    self.callback_time)
            except socket.error:
                # a socket is gone ?
                continue

            for sock in rlist:
                try:
                    self._rstats[sock.fileno()] += 1
                except socket.error:
                    # gone ?
                    pass

            for sock in wlist:
                try:
                    self._wstats[sock.fileno()] += 1
                except socket.error:
                    # gone ?
                    pass

            for sock in xlist:
                try:
                    self._xstats[sock.fileno()] += 1
                except socket.error:
                    # gone ?
                    pass

    def _aggregate(self, aggregate):
        raise NotImplementedError()

    def _persec(self, hits):
        if hits == 0:
            return 0
        return hits / self.callback_time

    def collect_stats(self):
        # sending hits by fd
        sockets = self.streamer.get_sockets()

        # we might lose a few hits here but it's ok
        for sock in sockets:
            info = {}
            fd = info['fd'] = sock.fileno()

            info['reads'] = self._persec(self._rstats[fd])
            self._rstats[fd] = 0

            info['writes'] = self._persec(self._wstats[fd])
            self._wstats[fd] = 0

            info['errors'] = self._persec(self._xstats[fd])
            self._xstats[fd] = 0

            yield info

        #raise NotImplementedError()
