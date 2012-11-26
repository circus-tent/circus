.. _hooks:

Hooks
#####

Circus provides four hooks that can be used to trigger actions when a watcher
is starting or stopping.

A typical use case is to control that all the conditions are met for a
process to start.

Let's say you have a watcher that runs *Redis* and a watcher that runs a
Python script that works with *Redis*.

With Circus you can order the startup by using the **priority** option::

    [watcher:queue-worker]
    cmd = python -u worker.py
    priority = 2

    [watcher:redis]
    cmd = redis-server
    priority = 1

With this setup, Circus will start **Redis** then the queue worker.

But Circus does not really control that *Redis* is up and running. It just
starts the process it was asked to start.

What we miss here is a way to control that *Redis* is started, and fully
functional. A function that controls this could be::

    import redis
    import time

    def check_redis(*args, **kw):
        time.sleep(.5)  # give it a chance to start
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        r.set('foo', 'bar')
        return r.get('foo') == 'bar'


This function can be plugged into Circus as a *after_start* hook::

    [watcher:queue-worker]
    cmd = python -u worker.py
    hooks.before_start = mycoolapp.myplugins.check_redis
    priority = 2

    [watcher:redis]
    cmd = redis-server
    priority = 1


Once Circus has started the **redis** watcher, it will start the
**queue-worker** watcher, since it follows the **priority** ordering.

Just before starting the second watcher, it will run the **check_redis**
function, and in case it returns **False** will abort the watcher
starting process.

Available hooks are:

- **before_start**: called before the watcher is started. If the hook
  returns **False** the startup is aborted.

- **after_start**: called before the watcher is started. If the hook
  returns **False** the watcher is immediatly stopped and the startup
  is aborted.

- **before_stop**: called before the watcher is stopped. The hook result
  is ignored.

- **after_stop**: called before the watcher is stopped. The hook result
  is ignored.


Hook signature
==============

A hook must follow this signature::

    def hook(watcher, arbiter, hook_name):
        ...


Where **watcher** is the **Watcher** class instance, **arbiter** the
**Arbiter** one, and **hook_name** the hook name.

You can ignore those but being able to use the watcher and/or arbiter
data and methods can be useful in some hooks.

Hook events
===========

Everytime a hook is run, its result is notified as an event in Circus.

There are two events related to hooks:

- **hook_success**:: a hook was successfully called. The event keys are
  **name** the name if the event, and **time**: the date of the events.

- **hook_failure**:: a hook has failed. The event keys are **name** the
  name if the event, **time**: the date of the events and
  **error**: the exception that occurred in the event, if any.
