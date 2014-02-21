import errno
import os
import tempfile
from datetime import datetime
from stat import ST_DEV, ST_INO
from circus import logger
from circus.py3compat import s, PY2


class _FileStreamBase(object):
    """Base class for all file writer handler classes"""
    # You may want to use another now method (not naive or a mock).
    now = datetime.now

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

    def close(self):
        self._file.close()

    def write_data(self, data):
        # data to write on file
        file_data = s(data['data'])

        # If we want to prefix the stream with the current datetime
        if self._time_format is not None:
            time = self.now().strftime(self._time_format)
            prefix = '{time} [{pid}] | '.format(time=time, pid=data['pid'])
            file_data = prefix + file_data.rstrip('\n')
            file_data = file_data.replace('\n', '\n' + prefix)
            file_data += '\n'

        # writing into the file
        try:
            self._file.write(file_data)
        except Exception:
            # we can strip the string down on Py3 but not on Py2
            if not PY2:
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
