.. _fordevs:

Circus for developers
#####################


Using Circus as a library
-------------------------

Circus provides high-level classes and functions that will let you manage
processes in your own applications.

For example, if you want to run four processes forever, you could write:

.. code-block:: python

    from circus import get_arbiter

    myprogram = {"cmd": "python myprogram.py", "numprocesses": 4}

    arbiter = get_arbiter([myprogram])
    try:
        arbiter.start()
    finally:
        arbiter.stop()

This snippet will run four instances of *myprogram* and watch them for you,
restarting them if they die unexpectedly.

To learn more about this, see :ref:`library`


Extending Circus
----------------

It's easy to extend Circus to create a more complex system, by listening to all
the **circusd** events via its pub/sub channel, and driving it via commands.

That's how the flapping feature works for instance: it listens to all the
processes dying, measures how often it happens, and stops the incriminated
watchers after too many restarts attempts.

Circus comes with a plugin system to help you write such extensions, and
a few built-in plugins you can reuse. See :ref:`plugins`.

You can also have a more subtile startup and shutdown behavior by using the
**hooks** system that will let you run arbitrary code before and after
some processes are started or stopped. See :ref:`hooks`.

Last but not least, you can also add new commands. See :ref:`addingcmds`.


Developers Documentation Index
------------------------------

.. toctree::
   :maxdepth: 1

   library
   writing-plugins
   writing-hooks
   adding-commands
