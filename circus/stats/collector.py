from circus import util
from circus import logger

from zmq.eventloop import ioloop



class BaseStatsCollector(ioloop.PeriodicCallback):

    def __init__(self, streamer, name, callback_time=1., io_loop=None):
        ioloop.PeriodicCallback.__init__(self, self._callback,
                                         callback_time * 1000, io_loop)
        self.get_pids = streamer.get_pids
        self.streamer = streamer
        self.publisher = streamer.publisher
        self.name = name

    def _callback(self):
        logger.debug('Publishing stats about {0}'.format(self.name))
        for stats in self.collect_stats():
            self.publisher.publish(self.name, stats)

    def collect_stats(self):
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
        for pid in self.get_pids(self.name):
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
    def _aggregate(self, aggregate):
        raise NotImplementedError()

    def collect_stats(self):
        aggregate = {}
        raise NotImplementedError()
