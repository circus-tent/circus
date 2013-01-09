import sys
import random

from datetime import datetime
from Queue import Queue

from circus.util import resolve_name
from circus.stream.file_stream import FileStream
from circus.stream.redirector import Redirector


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
        sys.stdout.write(data['data'])
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

      %Y-%M-%d %H:%M:%S

    Here is an example: ::

      [watcher:foo]
      cmd = python -m myapp.server
      stdout_stream.class = FancyStdoutStream
      stdout_stream.color = green
      stdout_stream.time_format = '%Y/%M/%d | %H:%M:%S'
    """

    # colors in order according to the ascii escape sequences
    colors = ['red', 'green', 'yellow', 'blue',
              'magenta', 'cyan', 'white']

    # Where we write output
    out = sys.stdout

    # Generate a datetime object
    now = datetime.now

    def __init__(self, color=None, time_format=None, *args, **kwargs):
        self.time_format = time_format or '%Y-%M-%d %H:%M:%S'

        # If no color is provided we pick one at random
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
        for line in data['data'].split('\n'):
            if line:
                self.out.write(self.prefix(data['pid']))
                self.out.write(line)
                # stop coloring
                self.out.write('\033[0m\n')
                self.out.flush()


def get_stream(conf):
    if not conf:
        return conf

    # we can have 'stream' or 'class' or 'filename'
    if 'filename' in conf:
        inst = FileStream(**conf)
    elif 'stream' in conf:
        inst = conf['stream']
    elif 'class' in conf:
        class_name = conf.pop('class')
        if not "." in class_name:
            class_name = "circus.stream.%s" % class_name
        inst = resolve_name(class_name)(**conf)
    else:
        raise ValueError("stream configuration invalid")

    # default refresh_time
    refresh_time = float(conf.get('refresh_time', 0.3))

    return {'stream': inst, 'refresh_time': refresh_time}


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
    refresh_time = redirect.get('refresh_time', 0.3)

    # finally setup the redirection
    return Redirector(stream, refresh_time, extra_info, buffer, loop=loop)
