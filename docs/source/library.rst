.. _library:

Circus Library
--------------

The Circus package is composed of a high-level :func:`get_trainer`
function and many classes. In most cases, using the high-level function
should be enough, as it creates everything that is needed for Circus to
run.

You can subclass Circus' classes if you need more granular
configurability.



The get_trainer function
========================

:func:`get_trainer` is just a convenience on the top of the various
circus classes. It creates a :class:`Trainer` instance with the provided
options, that runs a single :class:`Show` with a single :class:`Fly`.


.. autofunction:: circus.get_trainer

Example:

.. code-block:: python

   from circus import get_trainer

   trainer = get_trainer("myprogram", numflies=3)
   try:
       trainer.start()
   finally:
       trainer.stop()


The classes collection
======================

Circus provides a series of classes you can use to implement your own Circus
runner:

- :class:`Fly`: wraps a running process and provides a few helpers on the
  top of it.

- :class:`Show`: run several instances of :class:`Fly` against the same
  command. Manage the death and life of processes.

- :class:`Trainer`: run several instances of :class:`Show`.


.. autoclass:: circus.fly.Fly
   :members: pid, stdout, stderr, send_signal, stop, age, info,
             children, is_child, send_signal_child, send_signal_children,
             status


Example::

    >>> from circus.fly import Fly
    >>> fly = Fly('Top', 'top', shell=True)
    >>> fly.age()
    3.0107998847961426
    >>> fly.info()
    'Top: 6812  N/A tarek Zombie N/A N/A N/A N/A N/A'
    >>> fly.status
    1
    >>> fly.stop()
    >>> fly.status
    2
    >>> fly.info()
    'No such process (stopped?)'


.. autoclass:: circus.show.Show
   :members: send_msg, reap_flies, manage_flies, reap_and_manage_flies,
             spawn_flies, spawn_fly, kill_fly,kill_flies, send_signal_child, stop,start,
             restart, reload, do_action, get_opt


.. autoclass:: circus.trainer.Trainer
   :members: start, stop, reload, numflies, numshows, get_show, add_show

