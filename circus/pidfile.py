# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.  The
# Secondary License is the Apache License 2.0. You may obtain a copy of
# the Apache License 2 at http://www.apache.org/licenses/LICENSE-2.0.

import errno
import os
import tempfile


class Pidfile(object):
    """\
    Manage a PID file. If a specific name is provided
    it and '"%s.oldpid" % name' will be used. Otherwise
    we create a temp file using os.mkstemp.
    """

    def __init__(self, fname):
        self.fname = fname
        self.pid = None

    def create(self, pid):
        oldpid = self.validate()
        if oldpid:
            if oldpid == os.getpid():
                return
            raise RuntimeError("Already running on PID %s " \
                "(or pid file '%s' is stale)" % (os.getpid(), self.fname))

        self.pid = pid

        # Write pidfile
        fdir = os.path.dirname(self.fname)
        if fdir and not os.path.isdir(fdir):
            raise RuntimeError("%s doesn't exist. Can't create pidfile." % fdir)
        fd, fname = tempfile.mkstemp(dir=fdir)
        os.write(fd, "%s\n" % self.pid)
        if self.fname:
            os.rename(fname, self.fname)
        else:
            self.fname = fname
        os.close(fd)

        # set permissions to -rw-r--r--
        os.chmod(self.fname, 420)

    def rename(self, path):
        self.unlink()
        self.fname = path
        self.create(self.pid)

    def unlink(self):
        """ delete pidfile"""
        try:
            with open(self.fname, "r") as f:
                pid1 =  int(f.read() or 0)

            if pid1 == self.pid:
                os.unlink(self.fname)
        except:
            pass

    def validate(self):
        """ Validate pidfile and make it stale if needed"""
        if not self.fname:
            return
        try:
            with open(self.fname, "r") as f:
                wpid = int(f.read() or 0)

                if wpid <= 0:
                    return

                try:
                    os.kill(wpid, 0)
                    return wpid
                except OSError, e:
                    if e[0] == errno.ESRCH:
                        return
                    raise
        except IOError, e:
            if e[0] == errno.ENOENT:
                return
            raise
