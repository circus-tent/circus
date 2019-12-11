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

Circus works with:

- Python 2.7, 3.2 or 3.3
- zeromq >= 2.1.10 
    - The version of zeromq supported is ultimately determined by what version of `pyzmq <https://github.com/zeromq/pyzmq>`_ is installed by pip during circus installation.
    - Their current release supports 2.x (limited), 3.x, and 4.x ZeroMQ versions.
    - **Note**: If you are using PyPy instead of CPython, make sure to read their installation docs as ZeroMQ version support is not the same on PyPy.

When you install circus, the latest
versions of the Python dependencies will be pulled out for you.

You can also install them manually using the pip-requirements.txt
file we provide::

    $ pip install -r pip-requirements.txt


If you want to run the Web console you will need to install **circus-web**::

    $ pip install circus-web
