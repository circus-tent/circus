try:
    import ctypes
except MemoryError:
    # selinux execmem denial
    # https://bugzilla.redhat.com/show_bug.cgi?id=488396
    ctypes = None
except ImportError:
    # Python on Solaris compiled with Sun Studio doesn't have ctypes
    ctypes = None

import os
from pwd import getpwnam
from grp import getgrnam
import time

from circus import logger
from circus.util import Popen, to_uid, to_gid


_INFOLINE = ("%(pid)s %(username)s %(nice)s %(mem_info1)s "
             "%(mem_info2)s %(cpu)s %(mem)s %(ctime)s")


class Fly(object):
    def __init__(self, wid, cmd, wdir, shell, uid=None, gid=None, env=None):
        self.wid = str(wid)
        self.wdir = wdir
        self.shell = shell
        self.env = env
        self.cmd = cmd.replace('$WID', self.wid)

        self.uid = to_uid(uid)
        self.gid = to_gid(gid)

        def preexec_fn():
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

        logger.debug('running ' + self.cmd)
        self._worker = Popen(self.cmd.split(), cwd=self.wdir, shell=shell,
                             preexec_fn=preexec_fn, env=self.env)
        self.started = time.time()

    def poll(self):
        return self._worker.poll()

    def send_signal(self, sig):
        return self._worker.send_signal(sig)

    def stop(self):
        return self._worker.terminate()

    def age(self):
        return time.time() - self.started

    def info(self):
        """ return process info """
        info = _INFOLINE % self._worker.get_info()
        lines = ["%s: %s" % (self.wid, info)]

        for child in self._worker.get_children():
            info = _INFOLINE % child.get_info()
            lines.append("   %s" % info)

        return "\n".join(lines)

    def children(self):
        return ",".join(["%s" % child.pid
                         for child in self._worker.get_children()])

    def send_signal_child(self, pid, signum):
        pids = [child.pid for child in self._worker.get_children()]
        if pid in pids:
            child.send_signal(signum)
            return "ok"
        else:
            return "error: child not found"

    def send_signal_children(self, signum):
        for child in self._worker.get_children():
            child.send_signal(signum)
        return "ok"

    @property
    def pid(self):
        return self._worker.pid
