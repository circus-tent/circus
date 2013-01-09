.. _installation:

Installing Circus
#################

Use pip::

    $ pip install circus

Or download the archive on PyPI, extract and install it manually with::

    $ python setup.py install

If you want to try out Circus, see the :ref:`examples`.

If you are using debian or any debian based distribution, you also can use the
ppa to install circus, it's at
https://launchpad.net/~roman-imankulov/+archive/circus


zc.buildout
===========

We provide a `zc.buildout <http://www.buildout.org/>`_ configuration, you can
use it by simply running the bootstrap script, then calling buildout::

    $ python bootstrap.py
    $ bin/buildout


More on Requirements
====================

Circus uses:

- Python 2.6, 2.7 (3.x needs to be tested)
- zeromq >= 2.10

And on Python side:

- pyzmq 2.2.0.1
- iowait 0.1
- psutil 0.4.1

You can install all the py dependencies with the pip-requirements.txt file we
provide manually, or just install Circus and have the latest versions
of those libraries pulled for you::

    $ pip install -r pip-requirements.txt


If you want to run the Web console you will need to install **circus-web**::

    $ pip install circus-web
