import sys
import random

from datetime import datetime
try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty  # NOQA

from circus.util import resolve_name
from circus.stream.file_stream import FileStream
from circus.stream.file_stream import WatchedFileStream  # flake8: noqa
from circus.stream.file_stream import TimedRotatingFileStream  # flake8: noqa
from circus.stream.redirector import Redirector
from circus.py3compat import s


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
        sys.stdout.write(s(data['data']))
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

    def __init__(self, color=None, time_format=None, **kwargs):
        super(FancyStdoutStream, self).__init__(**kwargs)
        self.time_format = time_format or '%Y-%m-%d %H:%M:%S'
        if color not in self.colors:
            color = random.choice(self.colors)
        self.color_code = self.colors.index(color) + 1

    def prefix(self, pid):
        """
        Create a prefix for each line.

        This includes the ansi escape sequence for the color. This
        will not work on windows. For something more robust there is a
        good discussion over on Stack Overflow:

        http://stackoverflow.com/questions/287871
        """
        time = self.now().strftime(self.time_format)

        # start the coloring with the ansi escape sequence
        color = '\033[0;3%s;40m' % self.color_code

        prefix = '{time} [{pid}] | '.format(pid=pid, time=time)
        return color + prefix

    def __call__(self, data):
        for line in s(data['data']).split('\n'):
            if line:
                self.out.write(self.prefix(data['pid']))
                self.out.write(line)
                # stop coloring
                self.out.write('\033[0m\n')
                self.out.flush()


def get_stream(conf, reload=False):
    if not conf:
        return conf

    # we can have 'stream' or 'class' or 'filename'
    if 'class' in conf:
        class_name = conf.pop('class')
        if not "." in class_name:
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

    return {'stream': inst}


def get_pipe_redirector(redirect, extra_info=None, buffer=1024, loop=None):
    """Redirects data received in pipes to the redirect callable.

    The data is a mapping with a **data** key containing the data
    received from the pipe, extended with all values passed in
    **extra_info**

    Options:
    - **redirect**: the callable to send data to
    - **extra_info**: a mapping of values to add to each call
    - **buffer**: the size of the buffer when reading data
    - **loop**: the ioloop to use. If not provided will use the
      global IOLoop
    """
    # XXX backend is deprecated

    # get stream infos
    if 'stream' not in redirect:
        return

    stream = redirect.get('stream')

    # finally setup the redirection
    return Redirector(stream, extra_info, buffer, loop=loop)
