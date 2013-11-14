import warnings
from circus.plugins.statsd import BaseObserver
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
            raise NotImplementedError('watcher is mandatory for now.')
        self.max_cpu = float(config.get("max_cpu", 90))     # in %
        self.max_mem = config.get("max_mem")
        if self.max_mem is None:
            self.max_mem = 90.
        else:
            try:
                self.max_mem = float(self.max_mem)          # float -> %
            except ValueError:
                self.max_mem = human2bytes(self.max_mem)    # int -> absolute
        self.min_cpu = config.get("min_cpu")
        if self.min_cpu is not None:
            self.min_cpu = float(self.min_cpu)              # in %
        self.min_mem = config.get("min_mem")
        if self.min_mem is not None:
            try:
                self.max_mem = float(self.min_mem)          # float -> %
            except ValueError:
                self.max_mem = human2bytes(self.min_mem)    # int -> absolute
        self.health_threshold = float(config.get("health_threshold",
                                      75))  # in %
        self.max_count = int(config.get("max_count", 3))
        self._count_over_cpu = self._count_over_mem = 0
        self._count_under_cpu = self._count_under_mem = 0
        self._count_health = 0

    def look_after(self):
        info = self.call("stats", name=self.watcher)
        if info["status"] == "error":
            self.statsd.increment("_resource_watcher.%s.error" % self.watcher)
            return

        stats = info['info']
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
            max_cpu = max(cpus)
            max_mem = max(mems)
            max_mem_abs = max(mems_abs)
            min_cpu = min(cpus)
            min_mem = min(mems)
            min_mem_abs = min(mems_abs)
        else:
            # we dont' have any process running. max = 0 then
            max_cpu = max_mem = min_cpu = min_mem = 0
            max_mem_abs = min_mem_abs = 0

        if self.max_cpu and max_cpu > self.max_cpu:
            self.statsd.increment("_resource_watcher.%s.over_cpu" %
                                  self.watcher)
            self._count_over_cpu += 1
        else:
            self._count_over_cpu = 0

        if self.min_cpu is not None and min_cpu <= self.min_cpu:
            self.statsd.increment("_resource_watcher.%s.under_cpu" %
                                  self.watcher)
            self._count_under_cpu += 1
        else:
            self._count_under_cpu = 0

        if (isinstance(self.max_mem, float) and max_mem > self.max_mem or
                isinstance(self.max_mem, int) and max_mem_abs > self.max_mem):
            self.statsd.increment("_resource_watcher.%s.over_memory" %
                                  self.watcher)
            self._count_over_mem += 1
        else:
            self._count_over_mem = 0

        if self.min_mem is not None:
            if (isinstance(self.min_mem, float) and min_mem < self.min_mem or
                    isinstance(self.min_mem, int) and
                    min_mem_abs < self.min_mem):
                self.statsd.increment("_resource_watcher.%s.under_memory" %
                                      self.watcher)
                self._count_under_mem += 1
            else:
                self._count_under_mem = 0
        else:
            self._count_under_mem = 0

        if (self.health_threshold and
                (max_cpu + max_mem) / 2.0 > self.health_threshold):
            self.statsd.increment("_resource_watcher.%s.over_health" %
                                  self.watcher)
            self._count_health += 1
        else:
            self._count_health = 0

        if max([self._count_over_cpu, self._count_under_cpu,
                self._count_over_mem, self._count_under_mem,
                self._count_health]) > self.max_count:
            self.statsd.increment("_resource_watcher.%s.restarting" %
                                  self.watcher)
            # todo: restart only process instead of the whole watcher
            self.cast("restart", name=self.watcher)
            self._count_mem = self._count_health = self._count_mem = 0
