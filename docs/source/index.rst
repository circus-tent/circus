Circus Process Watcher 
======================

.. image:: images/circus-medium.png
   :align: right

Circus is a program that will let you run and watch multiple processes.

Circus can be driven through a CLI or used via its APIs.

It shares some of the goals Supervisord, BluePill and Daemontools.

To install it, check out :ref:`installation`


Using as a library
-------------------

Circus provides high-level Classes and functions that will let you run
processes. For example, if you just want to run 4 workers forever, you
can write.

.. code-block:: python

    from circus import get_trainer

    trainer = get_trainer("myprogram", 3)
    try:
        trainer.start()
    finally:
        trainer.stop()

This snippet will run 3 *myprogram* processes and watch them for you, 
restarting them if they die unexpectedly.

To learn more about this, see :ref:`library`


Using it through the command-line 
---------------------------------

Circus provides a command line script that can be used to manage one or more 
programs each running as one or more process instance.

It uses an ini-style file. Example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555

    [show:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    num_flies = 5

The file is then run using *circusd*::

    $ circusd example.ini

There's also a *circusctl* command line tool to query Circus to perform
actions like adding or removing workers, or getting back some usage
statistics.

To learn more about this, see :ref:`cli`


More documentation
------------------

.. toctree::
   :maxdepth: 2

   installation
   configuration
   cli
   library
   architecture


Contributions and Feedback
--------------------------

You can reach us for any feedback, bug report, or to contribute, at
https://github.com/mozilla-services/circus

We can also be found in the **#mozilla-circus** channel on freenode.net.
