.. _hooks:

Hooks
#####

Circus provides hooks that can be used to trigger actions upon watcher
events.  Available hooks are:

- **before_start**: called before the watcher is started. If the hook
  returns **False** the startup is aborted.

- **after_start**: called after the watcher is started. If the hook
  returns **False** the watcher is immediately stopped and the startup
  is aborted.

- **before_spawn**: called before the watcher spawns a new process.  If the
  hook returns **False** the watcher is immediately stopped and the startup is
  aborted.

- **after_spawn**: called after the watcher spawns a new process.  If the
  hook returns **False** the watcher is immediately stopped and the startup is
  aborted.

- **before_stop**: called before the watcher is stopped. The hook result
  is ignored.

- **after_stop**: called after the watcher is stopped. The hook result
  is ignored.

- **before_signal**: called before a signal is sent to a watcher's process. If
  the hook returns **False** the signal is not sent (except SIGKILL which is
  always sent)

- **after_signal**: called after a signal is sent to a watcher's process.

- **before_reap**: called before a process is reaped. `kwargs` contains
  `process_pid` and `time`.

- **after_reap**: called after a process is reaped. `kwargs` contains
  information about the process (`exit_code`, `process_pid`, `time`, `process_status`).
  In case a process exited by itself, `process_status` should worth
  either `circus.process.DEAD_OR_ZOMBIE` or `circus.process.UNEXISTING`.
  In case a process exited using a circus command, `process_status` will be `None`.

- **extended_stats**: called when stats are requested with extended=True.
  Used for adding process-specific stats to the regular stats output.

Example
=======

A typical use case is to control that all the conditions are met for a
process to start.  Let's say you have a watcher that runs *Redis* and a
watcher that runs a Python script that works with *Redis*.  With Circus
you can order the startup by using the ``priority`` option:

.. code-block:: ini

    [watcher:queue-worker]
    cmd = python -u worker.py
    priority = 1

    [watcher:redis]
    cmd = redis-server
    priority = 2

With this setup, Circus will start *Redis* first and then it will start the queue
worker.  But Circus does not really control that *Redis* is up and
running. It just starts the process it was asked to start.  What we miss
here is a way to control that *Redis* is started and fully functional. A function that controls this could be::

    import redis
    import time

    def check_redis(*args, **kw):
        time.sleep(.5)  # give it a chance to start
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        r.set('foo', 'bar')
        return r.get('foo') == 'bar'


This function can be plugged into Circus as an ``before_start`` hook:

.. code-block:: ini

    [watcher:queue-worker]
    cmd = python -u worker.py
    hooks.before_start = mycoolapp.myplugins.check_redis
    priority = 1

    [watcher:redis]
    cmd = redis-server
    priority = 2


Once Circus has started the **redis** watcher, it will start the
**queue-worker** watcher, since it follows the **priority** ordering.
Just before starting the second watcher, it will run the **check_redis**
function, and in case it returns **False** will abort the watcher
starting process.

If you'd like to use a hook that is defined in a relative python module
(as opposed to a globally installed module) then you need to define the
PYTHONPATH in *[env:watchername]*.

.. code-block:: ini

    [watcher:foo]
    copy_env = True
    hooks.before_start = hooks.my_hook.hook

    [env:foo]
    PYTHONPATH = $PYTHONPATH:$PWD

You can use environment variables like *$PWD* in the *PYTHONPATH*.


Hook signature
==============

A hook must follow this signature::

    def hook(watcher, arbiter, hook_name, **kwargs):
        ...
        # If you don't return True, the hook can change
        # the behavior of circus (depending on the hook)
        return True


Where **watcher** is the **Watcher** class instance, **arbiter** the
**Arbiter** one, **hook_name** the hook name and **kwargs** some additional
optional parameters (depending on the hook type).

The **after_spawn** hook adds the pid parameters::

    def after_spawn(watcher, arbiter, hook_name, pid, **kwargs):
        ...
        # If you don't return True, circus will kill the process
        return True

Where **pid** is the PID of the corresponding process.

Likewise, **before_signal** and **after_signal** hooks add pid and signum::

    def before_signal_hook(watcher, arbiter, hook_name, pid, signum, **kwargs):
        ...
        # If you don't return True, circus won't send the signum signal
        # (SIGKILL is always sent)
        return True

Where **pid** is the PID of the corresponding process and **signum** is the
corresponding signal.

You can ignore those but being able to use the watcher and/or arbiter
data and methods can be useful in some hooks.

Note that hooks are called with named arguments. So use the hook signature
without changing argument names.

The **extended_stats** hook has its own additional parameters in **kwargs**::

    def extended_stats_hook(watcher, arbiter, hook_name, pid, stats, **kwargs):
        ...

Where **pid** is the PID of the corresponding process and **stats** the
regular stats to be returned. Add your own stats into **stats**. An example
is in examples/uwsgi_lossless_reload.py.

As a last example, here is a super hook which can deal with all kind of signals::

    def super_hook(watcher, arbiter, hook_name, **kwargs):
        pid = None
        signum = None
        if hook_name in ('before_signal', 'after_signal'):
            pid = kwargs['pid']
            signum = kwargs['signum']
        ...
        return True

Hook events
===========

Everytime a hook is run, its result is notified as an event in Circus.

There are two events related to hooks:

- **hook_success**: a hook was successfully called. The event keys are
  **name** the name if the event, and **time**: the date of the events.

- **hook_failure**: a hook has failed. The event keys are **name** the
  name if the event, **time**: the date of the events and
  **error**: the exception that occurred in the event, if any.
