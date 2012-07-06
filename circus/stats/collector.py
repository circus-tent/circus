from collections import defaultdict
try:
    import gevent       # NOQA
    from gevent import monkey
    monkey.noisy = False
    monkey.patch_all()
    from gevent_zeromq import monkey_patch
    monkey_patch()
except ImportError:
    pass


from circus import util
from circus import logger

from zmq.eventloop import ioloop
from iowait import IOWait, SelectIOWait


class BaseStatsCollector(ioloop.PeriodicCallback):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        ioloop.PeriodicCallback.__init__(self, self._callback,
                                         callback_time * 1000, io_loop)
        self.streamer = streamer
        self.name = name

    def _callback(self):
        logger.debug('Publishing stats about {0}'.format(self.name))
        for stats in self.collect_stats():
            if stats is None:
                continue
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

        # finding out the older process
        ages = [stat['age'] for stat in stats if stat['age'] != 'N/A']
        if len(ages) == 0:
            res['age'] = 'N/A'
        else:
            res['age'] = max(ages)

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


# RESOLUTION is a value in seconds that will be used
# to determine the poller timeout of the sockets stats collector
#
# The PeriodicCallback calls the poller every LOOP_RES ms, and block
# for RESOLUTION seconds unless a read ready event occurs in the
# socket.
#
# This timer is used to limit the number of polls done on the
# socket, so the circusd-stats process don't eat all your CPU
# when you have a high-loaded socket.
#
_RESOLUTION = .1
_LOOP_RES = 10


class SocketStatsCollector(BaseStatsCollector):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        super(SocketStatsCollector, self).__init__(streamer, name,
                callback_time, io_loop)
        # if gevent is installed, we'll use a greenlet,
        # otherwise we'll use a thread
        try:
            import gevent       # NOQA
            self.greenlet = True
        except ImportError:
            self.greenlet = False

        self._rstats = defaultdict(int)
        if self.greenlet:
            self.poller = SelectIOWait()
        else:
            self.poller = IOWait()

        for sock, address, fd in self.streamer.get_sockets():
            self.poller.watch(sock, read=True, write=False)

        self._p = ioloop.PeriodicCallback(self._select, _LOOP_RES,
                                          io_loop=io_loop)

    def start(self):
        # starting the thread or greenlet
        self._p.start()
        super(SocketStatsCollector, self).start()

    def stop(self):
        self._p.stop()
        BaseStatsCollector.stop(self)

    def _select(self):
        # polling for events
        try:
            events = self.poller.wait(_RESOLUTION)
        except ValueError:
            return

        if len(events) == 0:
            return

        for socket, read, write in events:
            if read:
                self._rstats[socket.fileno()] += 1

    def _aggregate(self, aggregate):
        raise NotImplementedError()

    def collect_stats(self):
        # sending hits by sockets
        sockets = self.streamer.get_sockets()

        if len(sockets) == 0:
            yield None
        else:
            fds = [(address, sock.fileno(), fd)
                   for sock, address, fd in sockets]
            total = {'addresses': [], 'reads': 0}

            # we might lose a few hits here but it's ok
            for address, monitored_fd, fd in fds:
                info = {}
                info['fd'] = info['subtopic'] = fd
                info['reads'] = self._rstats[monitored_fd]
                total['reads'] += info['reads']
                total['addresses'].append(address)
                info['address'] = address
                self._rstats[monitored_fd] = 0
                yield info

            yield total
