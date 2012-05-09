import threading
import Queue
import time

from circus import util
from circus import logger


class StatsWorker(threading.Thread):
    def __init__(self, watcher, results, get_pids, interval=.5):
        threading.Thread.__init__(self)
        self.watcher = watcher
        self.running = False
        self.results = results
        self.interval = interval
        self.daemon = True
        self.get_pids = get_pids

    def _aggregate(self, aggregate):
        res = {'pid': aggregate.keys()}
        stats = aggregate.values()

        # aggregating CPU does not mean anything
        # but the average can be a good indicator
        cpu = [stat['cpu'] for stat in stats]
        if 'N/A' in cpu:
            res['cpu'] = 'N/A'
        else:
            res['cpu'] = sum(cpu) / len(cpu)

        # aggregating memory does make sense
        mem = [stat['mem'] for stat in stats]
        if 'N/A' in mem:
            res['mem'] = 'N/A'
        else:
            res['mem'] = sum(mem)
        return res

    def run(self):
        self.running = True
        while self.running:
            aggregate = {}

            # sending by pids
            for pid in self.get_pids(self.watcher):
                try:
                    info = util.get_info(pid, interval=self.interval)
                    aggregate[pid] = info
                except util.NoSuchProcess:
                    # the process is gone !
                    pass
                except Exception:
                    logger.exception('Failed to get info for %d' % pid)
                else:
                    self.results.put((self.watcher, pid, info))

            # now sending the aggregation
            self.results.put((self.watcher, None, self._aggregate(aggregate)))

            # sleep for accuracy
            time.sleep(self.interval)

    def stop(self):
        self.running = False


class StatsCollector(threading.Thread):

    def __init__(self, streamer, check_delay=1.):
        threading.Thread.__init__(self)
        self.daemon = True
        self.streamer = streamer
        self.running = False
        self.results = Queue.Queue()
        self.workers = {}
        self.check_delay = check_delay

    def run(self):
        self.running = True
        logger.debug('Starting the collector with %d workers' %
                        len(self.workers))

        # starting the workers
        for watcher in self.streamer.get_watchers():
            worker = StatsWorker(watcher, self.streamer.results,
                                 self.streamer.get_pids)
            self.workers[watcher] = worker
            worker.start()

        # now will maintain the list of watchers : if a watcher
        # is added or removed, we add or remove a thread here
        #
        # XXX use some all() and any() here
        while self.running:
            current = self.workers.keys()
            current.sort()
            watchers = self.streamer.get_watchers()
            watchers.sort()
            if watchers != current:
                # something has changed
                for watcher in watchers:
                    # added one
                    if watcher not in current:
                        worker = StatsWorker(watcher, self.streamer.results,
                                             self.streamer.get_pids)
                        self.workers[watcher] = worker
                        worker.start()
                for watcher in current:
                    if watcher not in watchers:
                        # one is gone
                        self.workers[watcher].stop()
                        del self.workers[watcher]

            # just sleep for a bit
            time.sleep(self.check_delay)

    def stop(self):
        self.running = False
        for worker in self.workers.values():
            worker.stop()
        logger.debug('Collector stopped')
