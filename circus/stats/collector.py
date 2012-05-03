import threading
import Queue

from circus import util


class StatsWorker(threading.Thread):
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


class StatsCollector(object):
    def __init__(self, stats, pool_size=10):
        self.stats = stats
        self.running = False
        self.pool_size = pool_size
        self.queue = Queue.Queue()
        self.results = Queue.Queue()
        self.workers = [StatsWorker(self.queue, self.results)
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
        for worker in self.workers:
            worker.stop()
