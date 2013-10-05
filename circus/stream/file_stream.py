import os
import tempfile
from datetime import datetime
from circus import logger
from zmq.utils.strtypes import u


class FileStream(object):
    # You may want to use another now method (not naive or a mock).
    now = datetime.now

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
        super(FileStream, self).__init__()
        if filename is None:
            fd, filename = tempfile.mkstemp()
            os.close(fd)
        self._filename = filename
        self._max_bytes = int(max_bytes)
        self._backup_count = int(backup_count)
        self._file = self._open()
        self._buffer = []
        self.time_format = time_format

    def _open(self):
        return open(self._filename, 'a+')

    def __call__(self, data):
        if self._should_rollover(data['data']):
            self._do_rollover()

        # If we want to prefix the stream with the current datetime
        for line in u(data['data']).split('\n'):
            if not line:
                continue
            if self.time_format is not None:
                self._file.write('{time} [{pid}] | '.format(
                    time=self.now().strftime(self.time_format),
                    pid=data['pid']))
            self._file.write(line)
            self._file.write('\n')
        self._file.flush()

    def close(self):
        self._file.close()

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
