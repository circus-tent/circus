from Queue import Queue

from circus.util import import_module

class QueueStream(Queue):
    def __call__(self, data):
        self.put(data)

    def close(self):
        pass


class FileStream(object):
    def __init__(self, filename):
        self._file = open(filename, 'a+')
        self._buffer = []

    def __call__(self, data):
        self._file.write(data['data'])
        self._file.flush()

    def close(self):
        self._file.close()


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

    backend_mod = import_module("circus.stream.s%s" % backend)
    backend_class = getattr(backend_mod, "Redirector")
    return backend_class(redirect, extra_info, buffer)
