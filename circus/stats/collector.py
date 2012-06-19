from circus import util
from circus import logger

from zmq.eventloop import ioloop


class StatsCollector(ioloop.PeriodicCallback):

    def __init__(self, streamer, watcher=None, callback_time=1., io_loop=None):
        ioloop.PeriodicCallback.__init__(self, self._callback,
                                         callback_time * 1000, io_loop)
        self.get_pids = streamer.get_pids
        self.streamer = streamer
        self.publisher = streamer.publisher
        self.watcher = watcher

    def _callback(self):
        logger.debug('Publishing stats about {0}'.format(self.watcher))
        process_name = None

        for pid, stats in self.collect_stats():
            if self.watcher == 'circus':
                if pid in self.streamer.circus_pids:
                    process_name = self.streamer.circus_pids[pid]
            self.publisher.publish(self.watcher, process_name, pid, stats)

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
        for pid in self.get_pids(self.watcher):
            try:
                info = util.get_info(pid)
                aggregate[pid] = info
                yield pid, info
            except util.NoSuchProcess:
                # the process is gone !
                pass
            except Exception, e:
                logger.exception('Failed to get info for %d. %s' % (pid,
                    str(e)))

        # now sending the aggregation
        yield None, self._aggregate(aggregate)
