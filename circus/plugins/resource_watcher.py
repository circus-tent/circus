from circus.plugins.statsd import BaseObserver


class ResourceWatcher(BaseObserver):

    def __init__(self, *args, **config):
        super(ResourceWatcher, self).__init__(*args, **config)
        self.service = config.get("service", None)
        self.max_cpu = float(config.get("max_cpu", 90))  # in %
        self.max_mem = float(config.get("max_mem", 90))  # in %
        self.health_threshold = float(config.get("health_threshold", 75))  # in %
        self.max_count = int(config.get("max_count", 3))

        self._count_cpu = self._count_mem = self._count_health = 0

    def look_after(self):
        info = self.call("stats", name=self.service)
        if info["status"] == "error":
            self.statsd.increment("_resource_watcher.%s.error" % self.service)
            return

        stats = info['info']

        cpus = []
        mems = []

        for sub_info in stats.itervalues():
            if isinstance(sub_info,  basestring):
                # dead processes have a string instead of actual info
                # ignore that
                continue
            cpus.append(sub_info['cpu'])
            mems.append(sub_info['mem'])

        max_cpu = max(cpus)
        max_mem = max(mems)

        if self.max_cpu and max_cpu > self.max_cpu:
            self.statsd.increment("_resource_watcher.%s.over_cpu" % self.service)
            self._count_cpu += 1
        else:
            self._count_cpu = 0

        if self.max_mem and max_mem > self.max_mem:
            self.statsd.increment("_resource_watcher.%s.over_memory" % self.service)
            self._count_mem += 1
        else:
            self._count_mem = 0

        if self.health_threshold and \
                (max_cpu + max_mem) / 2.0 > self.health_threshold:
            self.statsd.increment("_resource_watcher.%s.over_health" % self.service)
            self._count_health += 1
        else:
            self._count_health = 0

        if max([self._count_health, self._count_health,
                self._count_mem]) > self.max_count:
            self.statsd.increment("_resource_watcher.%s.restarting" % self.service)
            self.cast("restart", name=self.service)
            self._count_mem = self._count_health = self._count_mem = 0


