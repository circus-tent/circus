.. _library:

Circus Library
##############

The Circus package is composed of a high-level :func:`get_arbiter`
function and many classes. In most cases, using the high-level function
should be enough, as it creates everything that is needed for Circus to
run.

You can subclass Circus' classes if you need more granularity than what is
offered by the configuration.


The get_arbiter function
========================

:func:`get_arbiter` is just a convenience on top of the various
circus classes. It creates an :term:`arbiter` (class :class:`Arbiter`) instance
with the provided options, which in turn runs a single :class:`Watcher` with a
single :class:`Process`.


.. autofunction:: circus.get_arbiter

Example:

.. code-block:: python

   from circus import get_arbiter

   arbiter = get_arbiter([{"cmd": "myprogram", "numprocesses": 3}])
   try:
       arbiter.start()
   finally:
       arbiter.stop()


Classes
=======

Circus provides a series of classes you can use to implement your own process
manager:

- :class:`Process`: wraps a running process and provides a few helpers on top
  of it.

- :class:`Watcher`: run several instances of :class:`Process` against the same
  command. Manage the death and life of processes.

- :class:`Arbiter`: manages several :class:`Watcher` instances.


.. autoclass:: circus.process.Process
   :members: pid, stdout, stderr, send_signal, stop, age, info,
             children, is_child, send_signal_child, send_signal_children,
             status


Example::

    >>> from circus.process import Process
    >>> process = Process('Top', 'top', shell=True)
    >>> process.age()
    3.0107998847961426
    >>> process.info()
    'Top: 6812  N/A tarek Zombie N/A N/A N/A N/A N/A'
    >>> process.status
    1
    >>> process.stop()
    >>> process.status
    2
    >>> process.info()
    'No such process (stopped?)'


.. autoclass:: circus.watcher.Watcher
   :members: notify_event, reap_processes, manage_processes, reap_and_manage_processes,
             spawn_processes, spawn_process, kill_process,kill_processes, send_signal_child, stop,start,
             restart, reload, do_action


.. autoclass:: circus.arbiter.Arbiter
   :members: start, stop, reload, numprocesses, numwatchers, get_watcher, add_watcher
