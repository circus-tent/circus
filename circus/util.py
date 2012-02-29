from datetime import timedelta
import os

from psutil.error import AccessDenied
from psutil import Popen as PSPopen


_SYMBOLS = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')

def get_working_dir():
    # get current path, try to use PWD env first
    try:
        a = os.stat(os.environ['PWD'])
        b = os.stat(os.getcwd())
        if a.ino == b.ino and a.dev == b.dev:
            working_dir = os.environ['PWD']
        else:
            working_dir = os.getcwd()
    except:
        working_dir = os.getcwd()
    return working_dir

def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    if not isinstance(n, int):
        return n

    prefix = {}
    for i, s in enumerate(_SYMBOLS):
        prefix[s] = 1 << (i + 1) * 10

    for s in reversed(_SYMBOLS):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n


class Popen(PSPopen):
    def get_info(self):
        info = {}
        try:
            mem_info = self.get_memory_info()
            info['mem_info1'] = bytes2human(mem_info[0])
            info['mem_info2'] = bytes2human(mem_info[1])
        except AccessDenied:
            info['mem_info1'] = info['mem_info2'] = "N/A"

        try:
            info['cpu'] = self.get_cpu_percent(interval=0)
        except AccessDenied:
            info['cpu'] = "N/A"

        try:
            info['mem'] = round(self.get_memory_percent(), 1)
        except AccessDenied:
            info['mem'] = "N/A"

        try:
            cpu_times = self.get_cpu_times()
            ctime = timedelta(seconds=sum(cpu_times))
            ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                            str((ctime.seconds % 60)).zfill(2),
                            str(ctime.microseconds)[:2])
        except AccessDenied:
            ctime = "N/A"

        info['ctime'] = ctime

        for name in ('pid', 'username', 'nice'):
            try:
                info[name] = getattr(self, name)
            except AccessDenied:
                info[name] = 'N/A'

        return info
