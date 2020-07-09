import errno
from collections import defaultdict
import select
import socket

from circus import util
from circus import logger
from tornado import ioloop


class BaseStatsCollector(ioloop.PeriodicCallback):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        ioloop.PeriodicCallback.__init__(self, self._callback,
                                         callback_time * 1000)
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
        raise NotImplementedError()  # PRAGMA: NOCOVER


class WatcherStatsCollector(BaseStatsCollector):
    def _aggregate(self, aggregate):
        res = {'pid': list(aggregate.keys())}
        stats = list(aggregate.values())

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
            except Exception as e:
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
        self._rstats = defaultdict(int)
        self.sockets = [sock for sock, address, fd in self.streamer.sockets]
        self._p = ioloop.PeriodicCallback(self._select, _LOOP_RES)

    def start(self):
        self._p.start()
        super(SocketStatsCollector, self).start()

    def stop(self):
        self._p.stop()
        BaseStatsCollector.stop(self)

    def _select(self):
        try:
            rlist, wlist, xlist = select.select(self.sockets, [], [], .01)
        except socket.error as err:
            if err.errno in (errno.EBADF, errno.EINTR):
                return
            raise
        except select.error as err:
            if err.args[0] == errno.EINTR:
                return

        if len(rlist) == 0:
            return

        for sock in rlist:
            try:
                fileno = sock.fileno()
            except socket.error as err:
                if err.errno == errno.EBADF:
                    continue
                else:
                    raise

            self._rstats[fileno] += 1

    def _aggregate(self, aggregate):
        raise NotImplementedError()

    def collect_stats(self):
        # sending hits by sockets
        sockets = self.streamer.sockets

        if len(sockets) == 0:
            yield None
        else:
            fds = []

            for sock, address, fd in sockets:
                try:
                    fileno = sock.fileno()
                except socket.error as err:
                    if err.errno == errno.EBADF:
                        continue
                    else:
                        raise

                fds.append((address, fileno, fd))

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
