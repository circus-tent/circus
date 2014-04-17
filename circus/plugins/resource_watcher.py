import signal
import warnings
from circus.plugins.statsd import BaseObserver
from circus.util import to_bool


class ResourceWatcher(BaseObserver):

    def __init__(self, *args, **config):
        super(ResourceWatcher, self).__init__(*args, **config)
        self.watcher = config.get("watcher", None)
        self.service = config.get("service", None)
        if self.service is not None:
            warnings.warn("ResourceWatcher.service is deprecated "
                          "please use ResourceWatcher.watcher instead.",
                          category=DeprecationWarning)
            if self.watcher is None:
                self.watcher = self.service
        if self.watcher is None:
            self.statsd.stop()
            self.loop.close()
            raise NotImplementedError('watcher is mandatory for now.')
        self.max_cpu = float(config.get("max_cpu", 90))  # in %
        self.max_mem = float(config.get("max_mem", 90))  # in %
        self.min_cpu = config.get("min_cpu")
        if self.min_cpu is not None:
            self.min_cpu = float(self.min_cpu)  # in %
        self.min_mem = config.get("min_mem")
        if self.min_mem is not None:
            self.min_mem = float(self.min_mem)  # in %
        self.health_threshold = float(config.get("health_threshold",
                                      75))  # in %
        self.max_count = int(config.get("max_count", 3))

        self.process_children = to_bool(config.get("process_children", '0'))
        self.child_signal = int(config.get("child_signal", signal.SIGTERM))

        self._count_over_cpu = {}
        self._count_over_mem = {}
        self._count_under_cpu = {}
        self._count_under_mem = {}
        self._count_health = {}

    def look_after(self):
        info = self.call("stats", name=self.watcher)
        if info["status"] == "error":
            self.statsd.increment("_resource_watcher.%s.error" % self.watcher)
            return

        stats = info['info']

        max_cpu, max_mem, min_cpu, min_mem = self._collect_data(stats)
        self._process_index('parent', max_cpu, max_mem, min_cpu, min_mem)
        if not self.process_children:
            return

        for sub_info in stats.values():
            if isinstance(sub_info, dict):
                for child_info in sub_info['children']:
                    max_cpu, max_mem, min_cpu, min_mem = self._collect_data({
                        child_info['pid']: child_info
                    })
                    self._process_index(
                        child_info['pid'],
                        max_cpu,
                        max_mem,
                        min_cpu,
                        min_mem
                    )

    def _collect_data(self, stats):
        cpus = []
        mems = []

        for sub_info in stats.values():
            if isinstance(sub_info, dict):
                cpus.append(100 if sub_info['cpu'] == 'N/A' else
                            float(sub_info['cpu']))
                mems.append(100 if sub_info['mem'] == 'N/A' else
                            float(sub_info['mem']))

        if cpus:
            max_cpu = max(cpus)
            max_mem = max(mems)
            min_cpu = min(cpus)
            min_mem = min(mems)
        else:
            # we dont' have any process running. max = 0 then
            max_cpu = max_mem = min_cpu = min_mem = 0

        return max_cpu, max_mem, min_cpu, min_mem

    def _process_index(self, index, max_cpu, max_mem, min_cpu, min_mem):
        if index not in self._count_over_cpu or \
           index not in self._count_over_mem or \
           index not in self._count_under_cpu or \
           index not in self._count_under_mem or \
           index not in self._count_health:
            self._reset_index(index)

        if self.max_cpu and max_cpu > self.max_cpu:
            self.statsd.increment("_resource_watcher.%s.over_cpu" %
                                  self.watcher)
            self._count_over_cpu[index] += 1
        else:
            self._count_over_cpu[index] = 0

        if self.min_cpu is not None and min_cpu <= self.min_cpu:
            self.statsd.increment("_resource_watcher.%s.under_cpu" %
                                  self.watcher)
            self._count_under_cpu[index] += 1
        else:
            self._count_under_cpu[index] = 0

        if self.max_mem and max_mem > self.max_mem:
            self.statsd.increment("_resource_watcher.%s.over_memory" %
                                  self.watcher)
            self._count_over_mem[index] += 1
        else:
            self._count_over_mem[index] = 0

        if self.min_mem is not None and min_mem <= self.min_mem:
            self.statsd.increment("_resource_watcher.%s.under_memory" %
                                  self.watcher)
            self._count_under_mem[index] += 1
        else:
            self._count_under_mem[index] = 0

        if self.health_threshold and \
                (max_cpu + max_mem) / 2.0 > self.health_threshold:
            self.statsd.increment("_resource_watcher.%s.over_health" %
                                  self.watcher)
            self._count_health[index] += 1
        else:
            self._count_health[index] = 0

        if max([self._count_over_cpu[index], self._count_under_cpu[index],
                self._count_over_mem[index], self._count_under_mem[index],
                self._count_health[index]]) > self.max_count:
            self.statsd.increment("_resource_watcher.%s.restarting" %
                                  self.watcher)

            # todo: restart only process instead of the whole watcher
            if index == 'parent':
                self.cast("restart", name=self.watcher)
                self._reset_index(index)
            else:
                self.cast(
                    "signal",
                    name=self.watcher,
                    signum=self.child_signal,
                    child_pid=index
                )
                self._remove_index(index)

            self._reset_index(index)

    def _reset_index(self, index):
        self._count_over_cpu[index] = 0
        self._count_over_mem[index] = 0
        self._count_under_cpu[index] = 0
        self._count_under_mem[index] = 0
        self._count_health[index] = 0

    def _remove_index(self, index):
        del self._count_over_cpu[index]
        del self._count_over_mem[index]
        del self._count_under_cpu[index]
        del self._count_under_mem[index]
        del self._count_health[index]

    def stop(self):
        self.statsd.stop()
        super(ResourceWatcher, self).stop()
