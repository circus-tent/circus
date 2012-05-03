import threading
import Queue

from circus import util
from circus import logger


class StatsWorker(threading.Thread):
    def __init__(self, queue, results, delay=.1, interval=1.):
        threading.Thread.__init__(self)
        self.queue = queue
        self.delay = delay
        self.running = False
        self.results = results
        self.interval = interval
        self.daemon = True

    def run(self):
        self.running = True
        while self.running:
            try:
                watcher, pid = self.queue.get(timeout=self.delay)
                try:
                    info = util.get_info(pid, interval=self.interval)
                except util.NoSuchProcess:
                    # the process is gone !
                    pass
                else:
                    self.results.put((watcher, pid, info))
            except Queue.Empty:
                pass
            except Exception:
                logger.exception('Failed to get info for %d' % pid)

    def stop(self):
        self.running = False


class StatsCollector(threading.Thread):

    def __init__(self, streamer, pool_size=1):
        threading.Thread.__init__(self)
        self.daemon = True
        self.streamer = streamer
        self.running = False
        self.pool_size = pool_size
        self.queue = Queue.Queue()
        self.results = Queue.Queue()
        self.workers = [StatsWorker(self.queue, self.streamer.results)
                        for i in range(self.pool_size)]

    def run(self):
        self.running = True
        logger.debug('Starting the collector with %d workers' %
                        len(self.workers))
        for worker in self.workers:
            worker.start()

        while self.running:
            # filling a working queue with pids ordered by watchers
            for watcher in self.streamer.get_watchers():
                for pid in self.streamer.get_pids(watcher):
                    self.queue.put((watcher, pid))

    def stop(self):
        self.running = False
        for worker in self.workers:
            worker.stop()
        logger.debug('Collector stopped')
