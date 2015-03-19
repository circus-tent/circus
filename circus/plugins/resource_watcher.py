import signal
import warnings
from circus.plugins.statsd import BaseObserver
from circus.util import to_bool
from circus.util import human2bytes


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

        self.max_cpu = float(config.get("max_cpu", 90))     # in %
        self.max_mem = config.get("max_mem")

        if self.max_mem is None:
            self.max_mem = 90.
            self._max_percent = True
        else:
            try:
                self.max_mem = float(self.max_mem)          # float -> %
                self._max_percent = True
            except ValueError:
                self.max_mem = human2bytes(self.max_mem)    # int -> absolute
                self._max_percent = False

        self.min_cpu = config.get("min_cpu")
        if self.min_cpu is not None:
            self.min_cpu = float(self.min_cpu)              # in %
        self.min_mem = config.get("min_mem")
        if self.min_mem is not None:
            try:
                self.min_mem = float(self.min_mem)          # float -> %
                self._min_percent = True
            except ValueError:
                self.min_mem = human2bytes(self.min_mem)    # int -> absolute
                self._min_percent = True
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

        self._process_index('parent', self._collect_data(stats))
        if not self.process_children:
            return

        for sub_info in stats.values():
            if isinstance(sub_info, dict):
                for child_info in sub_info['children']:
                    data = self._collect_data({child_info['pid']: child_info})
                    self._process_index(child_info['pid'], data)

    def _collect_data(self, stats):
        data = {}
        cpus = []
        mems = []
        mems_abs = []

        for sub_info in stats.values():
            if isinstance(sub_info, dict):
                cpus.append(100 if sub_info['cpu'] == 'N/A' else
                            float(sub_info['cpu']))
                mems.append(100 if sub_info['mem'] == 'N/A' else
                            float(sub_info['mem']))
                mems_abs.append(0 if sub_info['mem_info1'] == 'N/A' else
                                human2bytes(sub_info['mem_info1']))

        if cpus:
            data['max_cpu'] = max(cpus)
            data['max_mem'] = max(mems)
            data['max_mem_abs'] = max(mems_abs)
            data['min_cpu'] = min(cpus)
            data['min_mem'] = min(mems)
            data['min_mem_abs'] = min(mems_abs)
        else:
            # we dont' have any process running. max = 0 then
            data['max_cpu'] = 0
            data['max_mem'] = 0
            data['min_cpu'] = 0
            data['min_mem'] = 0
            data['max_mem_abs'] = 0
            data['min_mem_abs'] = 0

        return data

    def _process_index(self, index, stats):

        if (index not in self._count_over_cpu or
                index not in self._count_over_mem or
                index not in self._count_under_cpu or
                index not in self._count_under_mem or
                index not in self._count_health):
            self._reset_index(index)

        if self.max_cpu and stats['max_cpu'] > self.max_cpu:
            self.statsd.increment("_resource_watcher.%s.over_cpu" %
                                  self.watcher)
            self._count_over_cpu[index] += 1
        else:
            self._count_over_cpu[index] = 0

        if self.min_cpu is not None and stats['min_cpu'] <= self.min_cpu:
            self.statsd.increment("_resource_watcher.%s.under_cpu" %
                                  self.watcher)
            self._count_under_cpu[index] += 1
        else:
            self._count_under_cpu[index] = 0

        if self.max_mem is not None:
            over_percent = (self._max_percent and
                            stats['max_mem'] > self.max_mem)
            over_value = (not self._max_percent and
                          stats['max_mem_abs'] > self.max_mem)

            if over_percent or over_value:
                self.statsd.increment("_resource_watcher.%s.over_memory" %
                                      self.watcher)
                self._count_over_mem[index] += 1
            else:
                self._count_over_mem[index] = 0
        else:
            self._count_over_mem[index] = 0

        if self.min_mem is not None:
            under_percent = (self._min_percent and
                             stats['min_mem'] < self.min_mem)
            under_value = (not self._min_percent and
                           stats['min_mem_abs'] < self.min_mem)

            if under_percent or under_value:
                self.statsd.increment("_resource_watcher.%s.under_memory" %
                                      self.watcher)
                self._count_under_mem[index] += 1
            else:
                self._count_under_mem[index] = 0
        else:
            self._count_under_mem[index] = 0

        max_cpu = stats['max_cpu']
        max_mem = stats['max_mem']

        if (self.health_threshold and
                (max_cpu + max_mem) / 2.0 > self.health_threshold):
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
