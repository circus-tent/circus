import sys
from Queue import Queue

from circus.util import import_module


class QueueStream(Queue):

    def __init__(self, **kwargs):
        Queue.__init__(self)

    def __call__(self, data):
        self.put(data)

    def close(self):
        pass


class FileStream(object):
    def __init__(self, filename=None, **kwargs):
        self._file = open(filename, 'a+')
        self._buffer = []

    def __call__(self, data):
        self._file.write(data['data'])
        self._file.flush()

    def close(self):
        self._file.close()


class StdoutStream(object):
    def __init__(self, **kwargs):
        pass

    def __call__(self, data):
        sys.stdout.write(data['data'])
        sys.stdout.flush()

    def close(self):
        pass


def get_pipe_redirector(redirect, backend='thread', extra_info=None,
        buffer=1024):
    """Redirects data received in pipes to the redirect callable.

    This function creates a separate thread that continuously reads
    data in the provided pipe and sends it to the provided callable.

    If Gevent and Gevent_zeromq are installed, this function will use
    a Greenlet for efficiency. It will fallback to a plain thread otherwise,
    and that may lead to poor performances and a lot of memory consumption
    when you have a lot of workers.

    The data is a mapping with a **data** key containing the data
    received from the pipe, extended with all values passed in
    **extra_info**

    Options:
    - **redirect**: the callable to send data to
    - **extra_info**: a mapping of values to add to each call
    - **buffer**: the size of the buffer when reading data
    """

    # get stream infos
    if 'stream' not in redirect:
        return
    stream = redirect.get('stream')
    refresh_time = redirect.get('refresh_time', 0.3)

    # get backend class
    backend_mod = import_module("circus.stream.s%s" % backend)
    backend_class = getattr(backend_mod, "Redirector")

    # finally setup the redirection
    return backend_class(stream, refresh_time, extra_info, buffer)
