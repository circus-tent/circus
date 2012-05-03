.. _installation:


Requirements
------------

- Python 2.6, 2.7 (3.x need to be tested)
- zeromq 2.10 or sup
- pyzmq

.. _note::

    You can optionnaly use circus with gevent. It will requires for now
    a forked version of `gevent_zeromq <https://github.com/tarekziade/gevent-zeromq>`_ .
    Hopefully the changes inside will be merged soon in zeromq (poller
    and ioloop monkey-patching).

Installing Circus
-----------------

Use pip::

    $ pip install circus

Or download the archive on PyPI, extract and install it manually with::

    $ python setup.py install

If you want to try out Circus, see the :ref:`examples`.
