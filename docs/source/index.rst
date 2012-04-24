Circus Process Watcher
======================

.. note::

   Before running Circus, make sure you read the :ref:`Security` page.

.. image:: images/circus-medium.png
   :align: right

Circus is a process watcher and runner. It can be driven via a 
command-line interface, or programmatically, in python, through its APIs.

It shares some of the goals of `Supervisord <http://supervisord.org>`_,
`BluePill <https://github.com/arya/bluepill>`_ and
`Daemontools <http://cr.yp.to/daemontools.html>`_.

To install it, check out :ref:`installation`


Using Circus via the command-line
---------------------------------

Circus provides a command-line script that can be used to manage one or
more :term:`watchers`. Each watcher can have one or more running 
:term:`processes`.

Circus' command-line tool is configurable using an ini-style
configuration file. Here is a minimal example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555

    [watcher:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    numprocesses = 5

    [watcher:anotherprogram]
    cmd = another_program
    numprocesses = 2


The file is then run using *circusd*::

    $ circusd example.ini

Circus also provides a management console, *circusctl*. You can use it to
perform actions such as adding or removing :term:`workers` or to display
various statistics.

To learn more about this, see :ref:`cli`


Using Circus as a Library
-------------------------

Circus provides high-level classes and functions that will let you manage
processes. For example, if you want to run four workers forever, you
can write:

.. code-block:: python

    from circus import get_arbiter

    arbiter = get_arbiter("myprogram", 4)
    try:
        arbiter.start()
    finally:
        arbiter.stop()

This snippet will run four instances of *myprogram* and watch them for you,
restarting them if they die unexpectedly.

To learn more about this, see :ref:`library`


Why should I use Circus instead of X ?
--------------------------------------

1. **Circus provides pub/sub and poll notifications via ZeroMQ**

  Circus has a :term:`pub/sub` channel you can subscribe to. This channel
  receives all events happening in Circus. For example, you can be
  notified when a process is :term:`flapping`, or build a client that
  triggers a warning when some processes are eating all the CPU or RAM.

  These events are sent via a ZeroMQ channel, which makes it different
  from the stdin stream Supervisord uses:

  - Circus sends events in a fire-and-forget fashion, so there's no
    need to manually loop through *all* listeners and maintain their
    states.
  - Subscribers can be located on a remote host.

  Circus also provides ways to get status updates via one-time polls
  on a req/rep channel. This means you can get your information without
  having to subscribe to a stream. The :ref:`cli` command provided by
  Circus uses this channel.

  See :ref:`examples`.


2. **Circus is (Python) developer friendly**

  While Circus can be driven entirely by a config file and the
  *circusctl* / *circusd* commands, it is easy to reuse all or part of
  the system to build your own custom process watcher in Python.

  Every layer of the system is isolated, so you can reuse independently:

  - the process wrapper (:class:`Process`)
  - the processes manager (:class:`Watcher`)
  - the global manager that runs several processes managers (:class:`Arbiter`)
  - and so on…


3. **Circus scales**

  One of the use cases of Circus is to manage thousands of processes without 
  adding overhead -- we're dedicated to focus on this.


More documentation
------------------

.. toctree::
   :maxdepth: 2

   installation
   configuration
   commands
   library
   deployment
   security
   examples
   coverage
   glossary


Contributions and Feedback
--------------------------

You can reach us for any feedback, bug report, or to contribute, at
https://github.com/mozilla-services/circus

We can also be found in the **#mozilla-circus** channel on freenode.net.