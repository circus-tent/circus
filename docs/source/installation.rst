.. _installation:

Installing Circus
-----------------

Use pip::

    $ pip install circus

Or download the archive on PyPI, extract and install it manually with::

    $ python setup.py install

If you want to try out Circus, see the :ref:`examples`.

If you are using debian or any debian based distributoin, you also can use the
ppa to install circus, it's at
https://launchpad.net/~roman-imankulov/+archive/circus

More on Requirements
--------------------

Circus uses:

- Python 2.6, 2.7 (3.x needs to be tested)
- zeromq >= 2.10

And on Python side:

- pyzmq 2.2.0
- iowait 0.1
- psutil 0.4.1

You can install all the py dependencies with the pip-requirements.txt file we
provide manually, or just install Circus and have the latest versions
of those libraries pulled for you::

    $ pip install -r pip-requirements.txt


If you want to run the Web console you will need more things:

- Mako 0.7.0
- MarkupSafe 0.15
- bottle 0.10.9
- anyjson 0.3.1
- gevent 0.13.7
- gevent-socketio 0.3.5-beta
- gevent-websocket 0.3.6
- greenlet 0.3.4
- beaker 1.6.3
- http://github.com/tarekziade/gevent-zeromq

Those can be installed with::

    $ pip install -r web-requirements.txt
