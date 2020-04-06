import errno
import os
import tempfile
from datetime import datetime
import time as time_
import re
from stat import ST_DEV, ST_INO, ST_MTIME
from circus import logger
from circus.util import to_str


class _FileStreamBase(object):
    """Base class for all file writer handler classes"""
    # You may want to use another now or fromtimestamp method
    # (not naive or a mock).
    now = datetime.now
    fromtimestamp = datetime.fromtimestamp

    def __init__(self, filename, time_format):
        if filename is None:
            fd, filename = tempfile.mkstemp()
            os.close(fd)
        self._filename = filename
        self._file = self._open()
        self._time_format = time_format
        self._buffer = []  # XXX - is this really needed?

    def _open(self):
        return open(self._filename, 'a+')

    def open(self):
        if self._file.closed:
            self._file = self._open()

    def close(self):
        self._file.close()

    def write_data(self, data):
        # data to write on file
        file_data = to_str(data['data'])

        # If we want to prefix the stream with the current datetime
        if self._time_format is not None:
            if 'timestamp' in data:
                time = self.fromtimestamp(data['timestamp'])
            else:
                time = self.now()
            time = time.strftime(self._time_format)
            prefix = '{time} [{pid}] | '.format(time=time, pid=data['pid'])
            file_data = prefix + file_data.rstrip('\n')
            file_data = file_data.replace('\n', '\n' + prefix)
            file_data += '\n'

        # writing into the file
        try:
            self._file.write(file_data)
        except Exception:
            file_data = file_data.encode('latin-1', errors='replace')
            file_data = file_data.decode('latin-1')
            self._file.write(file_data)

        self._file.flush()


class FileStream(_FileStreamBase):
    def __init__(self, filename=None, max_bytes=0, backup_count=0,
                 time_format=None, **kwargs):
        '''
        File writer handler which writes output to a file, allowing rotation
        behaviour based on Python's ``logging.handlers.RotatingFileHandler``.

        By default, the file grows indefinitely. You can specify particular
        values of max_bytes and backup_count to allow the file to rollover at
        a predetermined size.

        Rollover occurs whenever the current log file is nearly max_bytes in
        length. If backup_count is >= 1, the system will successively create
        new files with the same pathname as the base file, but with extensions
        ".1", ".2" etc. appended to it. For example, with a backup_count of 5
        and a base file name of "app.log", you would get "app.log",
        "app.log.1", "app.log.2", ... through to "app.log.5". The file being
        written to is always "app.log" - when it gets filled up, it is closed
        and renamed to "app.log.1", and if files "app.log.1", "app.log.2" etc.
        exist, then they are renamed to "app.log.2", "app.log.3" etc.
        respectively.

        If max_bytes is zero, rollover never occurs.

        You may also configure the timestamp format as defined by
        datetime.strftime.

        Here is an example: ::

          [watcher:foo]
          cmd = python -m myapp.server
          stdout_stream.class = FileStream
          stdout_stream.filename = /var/log/circus/out.log
          stdout_stream.time_format = %Y-%m-%d %H:%M:%S
        '''
        super(FileStream, self).__init__(filename, time_format)
        self._max_bytes = int(max_bytes)
        self._backup_count = int(backup_count)

    def __call__(self, data):
        if self._should_rollover(data['data']):
            self._do_rollover()

        self.write_data(data)

    def _do_rollover(self):
        """
        Do a rollover, as described in __init__().
        """
        if self._file:
            self._file.close()
            self._file = None
        if self._backup_count > 0:
            for i in range(self._backup_count - 1, 0, -1):
                sfn = "%s.%d" % (self._filename, i)
                dfn = "%s.%d" % (self._filename, i + 1)
                if os.path.exists(sfn):
                    logger.debug("Log rotating %s -> %s" % (sfn, dfn))
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self._filename + ".1"
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self._filename, dfn)
            logger.debug("Log rotating %s -> %s" % (self._filename, dfn))
        self._file = self._open()

    def _should_rollover(self, raw_data):
        """
        Determine if rollover should occur.

        Basically, see if the supplied raw_data would cause the file to exceed
        the size limit we have.
        """
        if self._file is None:                 # delay was set...
            self._file = self._open()
        if self._max_bytes > 0:                   # are we rolling over?
            self._file.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self._file.tell() + len(raw_data) >= self._max_bytes:
                return 1
        return 0


class WatchedFileStream(_FileStreamBase):
    def __init__(self, filename=None, time_format=None, **kwargs):
        '''
        File writer handler which writes output to a file, allowing an external
        log rotation process to handle rotation, like Python's
        ``logging.handlers.WatchedFileHandler``.

        By default, the file grows indefinitely, and you are responsible for
        ensuring that log rotation happens with some external tool like
        logrotate.

        You may also configure the timestamp format as defined by
        datetime.strftime.

        Here is an example: ::

          [watcher:foo]
          cmd = python -m myapp.server
          stdout_stream.class = WatchedFileStream
          stdout_stream.filename = /var/log/circus/out.log
          stdout_stream.time_format = %Y-%m-%d %H:%M:%S
        '''
        super(WatchedFileStream, self).__init__(filename, time_format)
        self.dev, self.ino = -1, -1
        self._statfile()

    def _statfile(self):
        stb = os.fstat(self._file.fileno())
        self.dev, self.ino = stb[ST_DEV], stb[ST_INO]

    def _statfilename(self):
        try:
            stb = os.stat(self._filename)
            return stb[ST_DEV], stb[ST_INO]
        except OSError as err:
            if err.errno == errno.ENOENT:
                return -1, -1
            else:
                raise

    def __call__(self, data):
        # stat the filename to see if the file we opened still exists. If the
        # ino or dev doesn't match, we need to open a new file handle
        dev, ino = self._statfilename()
        if dev != self.dev or ino != self.ino:
            self._file.flush()
            self._file.close()
            self._file = self._open()
            self._statfile()

        self.write_data(data)


_MIDNIGHT = 24 * 60 * 60  # number of seconds in a day


class TimedRotatingFileStream(FileStream):

    def __init__(self, filename=None, backup_count=0, time_format=None,
                 rotate_when=None, rotate_interval=1, utc=False, **kwargs):
        '''
        File writer handler which writes output to a file, allowing rotation
        behaviour based on Python's
        ``logging.handlers.TimedRotatingFileHandler``.

        The parameters are the same as ``FileStream`` except max_bytes.

        In addition you can specify extra parameters:

        - utc: if True, times in UTC will be used. otherwise local time is
          used. Default: False.
        - rotate_when: the type of interval. Can be S, M, H, D,
          'W0'-'W6' or 'midnight'. See Python's TimedRotatingFileHandler
          for more information.
        - rotate_interval: Rollover interval in seconds. Default: 1

        Here is an example: ::

          [watcher:foo]
          cmd = python -m myapp.server
          stdout_stream.class = TimedRotatingFileStream
          stdout_stream.filename = /var/log/circus/out.log
          stdout_stream.time_format = %Y-%m-%d %H:%M:%S
          stdout_stream.utc = True
          stdout_stream.rotate_when = H
          stdout_stream.rotate_interval = 1

        '''
        super(TimedRotatingFileStream,
              self).__init__(filename=filename, backup_count=backup_count,
                             time_format=time_format, utc=False,
                             **kwargs)

        self._utc = bool(utc)
        self._when = rotate_when

        if self._when == "S":
            self._interval = 1
            self._suffix = "%Y%m%d%H%M%S"
            self._ext_match = r"^\d{4}\d{2}\d{2}\d{2}\d{2}\d{2}$"
        elif self._when == "M":
            self._interval = 60
            self._suffix = "%Y%m%d%H%M"
            self._ext_match = r"^\d{4}\d{2}\d{2}\d{2}\d{2}$"
        elif self._when == "H":
            self._interval = 60 * 60
            self._suffix = "%Y%m%d%H"
            self._ext_match = r"^\d{4}\d{2}\d{2}\d{2}$"
        elif self._when in ("D", "MIDNIGHT"):
            self._interval = 60 * 60 * 24
            self._suffix = "%Y%m%d"
            self._ext_match = r"^\d{4}\d{2}\d{2}$"
        elif self._when.startswith("W"):
            self._interval = 60 * 60 * 24 * 7
            if len(self._when) != 2:
                raise ValueError("You must specify a day for weekly\
rollover from 0 to 6 (0 is Monday): %s" % self._when)
            if self._when[1] < "0" or self._when[1] > "6":
                raise ValueError("Invalid day specified\
for weekly rollover: %s" % self._when)
            self._day_of_week = int(self._when[1])
            self._suffix = "%Y%m%d"
            self._ext_match = r"^\d{4}\d{2}\d{2}$"
        else:
            raise ValueError("Invalid rollover interval specified: %s" %
                             self._when)

        self._ext_match = re.compile(self._ext_match)
        self._interval = self._interval * int(rotate_interval)

        if os.path.exists(self._filename):
            t = os.stat(self._filename)[ST_MTIME]
        else:
            t = int(time_.time())
        self._rollover_at = self._compute_rollover(t)

    def _do_rollover(self):
        if self._file:
            self._file.close()
            self._file = None

        current_time = int(time_.time())
        dst_now = time_.localtime(current_time)[-1]
        t = self._rollover_at - self._interval
        if self._utc:
            time_touple = time_.gmtime(t)
        else:
            time_touple = time_.localtime(t)
            dst_then = time_touple[-1]
            if dst_now != dst_then:
                if dst_now:
                    addend = 3600
                else:
                    addend = -3600
                time_touple = time_.localtime(t + addend)

        dfn = self._filename + "." + time_.strftime(self._suffix, time_touple)

        if os.path.exists(dfn):
            os.remove(dfn)

        if os.path.exists(self._filename):
            os.rename(self._filename, dfn)
            logger.debug("Log rotating %s -> %s" % (self._filename, dfn))

        if self._backup_count > 0:
            for f in self._get_files_to_delete():
                os.remove(f)

        self._file = self._open()

        new_rollover_at = self._compute_rollover(current_time)
        while new_rollover_at <= current_time:
            new_rollover_at = new_rollover_at + self._interval
        self._rollover_at = new_rollover_at

    def _compute_rollover(self, current_time):
        result = current_time + self._interval

        if self._when == "MIDNIGHT" or self._when.startswith("W"):
            if self._utc:
                t = time_.gmtime(current_time)
            else:
                t = time_.localtime(current_time)
            current_hour = t[3]
            current_minute = t[4]
            current_second = t[5]

            r = _MIDNIGHT - ((current_hour * 60 + current_minute) *
                             60 + current_second)
            result = current_time + r

            if self._when.startswith("W"):
                day = t[6]
                if day != self._day_of_week:
                    days_to_wait = self._day_of_week - day
                else:
                    days_to_wait = 6 - day + self._day_of_week + 1
                new_rollover_at = result + (days_to_wait * (60 * 60 * 24))
                if not self._utc:
                    dst_now = t[-1]
                    dst_at_rollover = time_.localtime(new_rollover_at)[-1]
                    if dst_now != dst_at_rollover:
                        if not dst_now:
                            addend = -3600
                        else:
                            addend = 3600
                        new_rollover_at += addend
                result = new_rollover_at

        return result

    def _get_files_to_delete(self):
        dirname, basename = os.path.split(self._filename)
        prefix = basename + "."
        plen = len(prefix)

        result = []
        for filename in os.listdir(dirname):
            if filename[:plen] == prefix:
                suffix = filename[plen:]
                if self._ext_match.match(suffix):
                    result.append(os.path.join(dirname, filename))
        result.sort()
        if len(result) < self._backup_count:
            return []
        return result[:len(result) - self._backup_count]

    def _should_rollover(self, raw_data):
        """
        Determine if rollover should occur.

        record is not used, as we are just comparing times, but it is needed so
        the method signatures are the same
        """
        t = int(time_.time())
        if t >= self._rollover_at:
            return 1
        return 0
