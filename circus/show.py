from circus.fly import Fly
import time


class Show(object):

    def __init__(self, name, cmd, num_flies, warmup_delay):
        self.name = name
        self.num_flies = num_flies
        self.warmup_delay = warmup_delay
        self.cmd = cmd
        self._fly_counter = 0
        self.flies = {}

    def __len__(self):
        return len(self.flies)

    def handle_numflies(self, *args):
        return str(self.num_flies)

    def reap_flies(self):
        for wid, fly in self.flies.items():
            if fly.poll() is not None:
                self.flies.pop(wid)

    def manage_flies(self):
        if len(self.flies.keys()) < self.num_flies:
            self.spawn_flies()

        flies = self.flies.keys()
        flies.sort()
        while len(flies) > self.num_flies:
            wid = flies.pop(0)
            fly = self.flies.pop(wid)
            self.kill_fly(fly)

    def spawn_flies(self):
        for i in range(self.num_flies - len(self.flies.keys())):
            self.spawn_fly()
            time.sleep(self.warmup_delay)

    def spawn_fly(self):
        self._fly_counter += 1
        fly = Fly(self._fly_counter, self.cmd)
        print 'running %s fly [pid %d]' % (self.name, fly.pid)
        self.flies[self._fly_counter] = fly

    # TODO: we should manage more flies here.
    def kill_fly(self, fly):
        print "kill fly %s" % fly.pid
        fly.terminate()

    def kill_flies(self):
        for wid in self.flies.keys():
            try:
                fly = self.flies.pop(wid)
                self.kill_fly(fly)
            except OSError, e:
                if e.errno != errno.ESRCH:
                    raise

    def handle_quit(self, *args):
        self.kill_flies()
        self.num_flies = 0
        return "ok"

    def handle_reload(self, *args):
        for i in range(self.num_flies):
            self.spawn_fly()
        self.manage_flies()
        return "ok"

    handle_hup = handle_reload

    def handle_ttin(self, *args):
        self.num_flies += 1
        self.manage_flies()
        return str(self.num_flies)

    def handle_ttou(self, *args):
        self.num_flies -= 1
        self.manage_flies()
        return str(self.num_flies)
