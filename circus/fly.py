# This file is part of circus. See the NOTICE for more information.

from psutil import Popen
from psutil.error import AccessDenied
import os
from pwd import getpwnam
from grp import getgrnam
from datetime import timedelta
import time


def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """

    if not isinstance(n, int):
        return n

    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n

def info_line(p):
    try:
        mem_info = p.get_memory_info()
    except AccessDenied:
        mem_info = ("N/A", "N/A")

    try:
        cpu = p.get_cpu_percent(interval=0)
    except AccessDenied:
        cpu = "N/A"

    try:
        mem = round(p.get_memory_percent(), 1)
    except AccessDenied:
        mem = "N/A"

    try:
        cpu_times = p.get_cpu_times()

        ctime = timedelta(seconds=sum(cpu_times))
        ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                          str((ctime.seconds % 60)).zfill(2),
                          str(ctime.microseconds)[:2])

    except AccessDenied:
        ctime = "N/A"

    return "%s %s %s %s %s %s %s %s" % (p.pid, p.username, p.nice,
            bytes2human(mem_info[1]), bytes2human(mem_info[0]), cpu,
            mem, ctime)


class Fly(object):
    def __init__(self, wid, cmd, wdir, shell, uid=None, gid=None):
        self.wid = str(wid)
        self.wdir = wdir
        self.shell = shell
        self.cmd = cmd.replace('$WID', self.wid)
        if uid is not None:
            self.uid = getpwnam(uid)[2]
        else:
            self.uid = None

        if gid is not None:
            self.gid = getgrnam(gid)[2]
        else:
            self.gid = None

        def preexec_fn():
            if self.uid:
                os.setgid(self.uid)
            if self.gid:
                os.setuid(self.gid)

        self._worker = Popen(self.cmd.split(), cwd=self.wdir, shell=shell,
                             preexec_fn=preexec_fn)
        self.started = time.time()

    def poll(self):
        return self._worker.poll()

    def send_signal(self, sig):
        return self._worker.send_signal(sig)

    def terminate(self):
        return self._worker.terminate()

    def age(self):
        return time.time() - self.started

    def info(self):
        """ return process info """
        lines = ["%s: %s" % (self.wid, info_line(self._worker))]
        try:
            for child in self._worker.get_children():
                lines.append("   %s" % info_line(child))
        except AccessDenied:
            pass
        return "\n".join(lines)

    def children(self):
        try:
            return ",".join(["%s" % child.pid \
                    for child in self._worker.get_children()])
        except AccessDenied:
            return "error: access denied"

    def send_signal_child(self, pid, signum):
        try:
            pids = [child.pid for child in self._worker.get_children()]
            if pid in pids:
                child.send_signal(signum)
                return "ok"
            else:
                return "error: child not found"
        except AccessDenied:
            return "error: access denied"

    def send_signal_children(self, signum):
        try:
            for child in self._worker.get_children():
                child.send_signal(signum)
            return "ok"
        except AccessDenied:
            return "error: access denied"

    @property
    def pid(self):
        return self._worker.pid
