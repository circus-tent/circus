try:
    import ctypes
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    ctypes = None       # NOQA
except ImportError:
    # Python on Solaris compiled with Sun Studio doesn't have ctypes
    ctypes = None       # NOQA

import os
import time

from psutil import Popen

from circus import logger
from circus.util import get_info, to_uid, to_gid, debuglog


_INFOLINE = ("%(pid)s  %(cmdline)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


class Fly(object):
    def __init__(self, wid, cmd, working_dir, shell, uid=None, gid=None,
                 env=None):
        self.wid = wid
        self.working_dir = working_dir
        self.shell = shell
        self.env = env
        self.cmd = cmd.replace('$WID', str(self.wid))

        self.uid = to_uid(uid)
        self.gid = to_gid(gid)

        def preexec_fn():
            os.setsid()
            if self.gid:
                try:
                    os.setgid(self.gid)
                except OverflowError:
                    if not ctypes:
                        raise
                    # versions of python < 2.6.2 don't manage unsigned int for
                    # groups like on osx or fedora
                    os.setgid(-ctypes.c_int(-self.gid).value)

            if self.uid:
                os.setuid(self.uid)

        self._worker = Popen(self.cmd.split(), cwd=self.working_dir,
                             shell=self.shell, preexec_fn=preexec_fn,
                             env=self.env, close_fds=True)
        self.started = time.time()

    @debuglog
    def poll(self):
        return self._worker.poll()

    @debuglog
    def send_signal(self, sig):
        return self._worker.send_signal(sig)

    @debuglog
    def stop(self):
        if self._worker.poll() is None:
            return self._worker.terminate()

    def age(self):
        return time.time() - self.started

    def info(self):
        """ return process info """
        info = _INFOLINE % get_info(self._worker)
        lines = ["%s: %s" % (self.wid, info)]

        for child in self._worker.get_children():
            info = _INFOLINE % get_info(child)
            lines.append("   %s" % info)

        return "\n".join(lines)

    def children(self):
        return ",".join(["%s" % child.pid
                         for child in self._worker.get_children()])

    @debuglog
    def send_signal_child(self, pid, signum):
        pids = [child.pid for child in self._worker.get_children()]
        if pid in pids:
            child.send_signal(signum)
            return "ok"
        else:
            return "error: child not found"

    @debuglog
    def send_signal_children(self, signum):
        for child in self._worker.get_children():
            child.send_signal(signum)
        return "ok"

    @property
    def pid(self):
        return self._worker.pid
