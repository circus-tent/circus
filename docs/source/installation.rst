.. _installation:

Installing Circus
#################

Circus is a Python package which is published on PyPI - the Python Package Index.

The simplest way to install it is to use pip, a tool for installing and managing Python packages::

    $ pip install circus

Or download the `archive on PyPI <https://pypi.python.org/pypi/circus>`_,
extract and install it manually with::

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

- Python 2.6, 2.7, 3.2 or 3.3
- zeromq >= 2.1.10 (you can use the 2.x or the 3.x series)

When you install circus, the latest
versions of the Python dependencies will be pulled out for you.

You can also install them manually using the pip-requirements.txt
file we provide::

    $ pip install -r pip-requirements.txt


If you want to run the Web console you will need to install **circus-web**::

    $ pip install circus-web
