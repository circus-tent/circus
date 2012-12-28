import sys
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
