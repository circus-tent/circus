import sys
import random

from datetime import datetime
from queue import Queue, Empty  # noqa: F401

from circus.util import resolve_name, to_str
from circus.stream.file_stream import FileStream
from circus.stream.file_stream import WatchedFileStream  # noqa: F401
from circus.stream.file_stream import TimedRotatingFileStream  # noqa: F401
from circus.stream.redirector import Redirector  # noqa: F401


class QueueStream(Queue):

    def __init__(self, **kwargs):
        Queue.__init__(self)

    def __call__(self, data):
        self.put(data)

    def close(self):
        pass


class StdoutStream(object):
    def __init__(self, **kwargs):
        pass

    def __call__(self, data):
        sys.stdout.write(to_str(data['data']))
        sys.stdout.flush()

    def close(self):
        pass


class FancyStdoutStream(StdoutStream):
    """
    Write output from watchers using different colors along with a
    timestamp.

    If no color is selected a color will be chosen at random. The
    available ascii colors are:

      - red
      - green
      - yellow
      - blue
      - magenta
      - cyan
      - white

    You may also configure the timestamp format as defined by
    datetime.strftime. The default is: ::

      %Y-%m-%d %H:%M:%S

    Here is an example: ::

      [watcher:foo]
      cmd = python -m myapp.server
      stdout_stream.class = FancyStdoutStream
      stdout_stream.color = green
      stdout_stream.time_format = '%Y/%m/%d | %H:%M:%S'
    """

    # colors in order according to the ascii escape sequences
    colors = ['red', 'green', 'yellow', 'blue',
              'magenta', 'cyan', 'white']

    # Where we write output
    out = sys.stdout

    # Generate a datetime object
    now = datetime.now
    fromtimestamp = datetime.fromtimestamp

    def __init__(self, color=None, time_format=None, **kwargs):
        super(FancyStdoutStream, self).__init__(**kwargs)
        self.time_format = time_format or '%Y-%m-%d %H:%M:%S'
        if color not in self.colors:
            color = random.choice(self.colors)
        self.color_code = self.colors.index(color) + 1

    def prefix(self, data):
        """
        Create a prefix for each line.

        This includes the ansi escape sequence for the color. This
        will not work on windows. For something more robust there is a
        good discussion over on Stack Overflow:

        http://stackoverflow.com/questions/287871
        """
        pid = data['pid']
        if 'timestamp' in data:
            time = self.fromtimestamp(data['timestamp'])
        else:
            time = self.now()
        time = time.strftime(self.time_format)

        # start the coloring with the ansi escape sequence
        color = '\033[0;3%s;40m' % self.color_code

        prefix = '{time} [{pid}] | '.format(pid=pid, time=time)
        return color + prefix

    def __call__(self, data):
        for line in to_str(data['data']).split('\n'):
            if line:
                self.out.write(self.prefix(data))
                self.out.write(line)
                # stop coloring
                self.out.write('\033[0m\n')
                self.out.flush()


def get_stream(conf, reload=False):
    if conf:
        # we can have 'stream' or 'class' or 'filename'
        if 'class' in conf:
            class_name = conf.pop('class')
            if "." not in class_name:
                cls = globals()[class_name]
                inst = cls(**conf)
            else:
                inst = resolve_name(class_name, reload=reload)(**conf)
        elif 'stream' in conf:
            inst = conf['stream']
        elif 'filename' in conf:
            inst = FileStream(**conf)
        else:
            raise ValueError("stream configuration invalid")

        return inst
