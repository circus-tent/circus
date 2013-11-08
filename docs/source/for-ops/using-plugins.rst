.. _plugins:

Using built-in plugins
######################

Circus comes with a few built-in plugins. This section presents these plugins and their configuration options.

Statsd
======

    **use**
        set to 'circus.plugins.statsd.StatsdEmitter'

    **application_name**
        the name used to identify the bucket prefix to emit the stats to (it will be prefixed with ``circus.`` and suffixed with ``.watcher``)

    **host**
        the host to post the statds data to

    **port**
        the port the statsd daemon listens on

    **sample_rate**
        if you prefer a different sample rate than 1, you can set it here


FullStats
=========

    An extension on the Statsd plugin that is also publishing the process stats. As
    such it has the same configuration options as Statsd and the following.

    **use**
        set to ``circus.plugins.statsd.FullStats``

    **loop_rate**
        the frequency the plugin should ask for the stats in seconds. Default: 60.


RedisObserver
=============

    This services observers a redis process for you, publishes the information to statsd
    and offers to restart the watcher when it doesn't react in a given timeout. This
    plugin requires `redis-py <https://github.com/andymccurdy/redis-py>`_  to run.

    It has the same configuration as statsd and adds the following:

    **use**
        set to   ``circus.plugins.redis_observer.RedisObserver``

    **loop_rate**
        the frequency the plugin should ask for the stats in seconds. Default: 60.

    **redis_url**
        the database to check for as a redis url. Default: "redis://localhost:6379/0"

    **timeout**
        the timeout in seconds the request can take before it is considered down. Defaults to 5.

    **restart_on_timeout**
        the name of the process to restart when the request timed out. No restart triggered when not given. Default: None.


HttpObserver
============

    This services observers a http process for you by pinging a
    certain website regularly. Similar to the redis observer it offers
    to restart the watcher on an error. It requires `tornado
    <http://www.tornadoweb.org>`_ to run.

    It has the same configuration as statsd and adds the following:

    **use**
        set to ``circus.plugins.http_observer.HttpObserver``

    **loop_rate**
        the frequency the plugin should ask for the stats in seconds. Default: 60.

    **check_url**
        the url to check for. Default: ``http://localhost/``

    **timeout**
        the timeout in seconds the request can take before it is considered down. Defaults to 10.

    **restart_on_error**
        the name of the process to restart when the request timed out or returned
        any other kind of error. No restart triggered when not given. Default: None.



ResourceWatcher
===============

    This services watches the resources of the given process and triggers a restart when they exceed certain limitations too often in a row.

    It has the same configuration as statsd and adds the following:

    **use**
        set to ``circus.plugins.resource_watcher.ResourceWatcher``

    **loop_rate**
        the frequency the plugin should ask for the stats in seconds. Default: 60.

    **watcher**
        the watcher this resource watcher should be looking after.
        (previously called ``service`` but ``service`` is now deprecated)

    **max_cpu**
        The maximum cpu one process is allowed to consume (in %). Default: 90

    **min_cpu**
        The minimum cpu one process should consume (in %). Default: None (no minimum)
        You can set the min_cpu to 0 (zero), in this case if one process consume exactly 0% cpu, it will trigger an exceeded limit.

    **max_mem**
        The amount of memory one process of this watcher is allowed to consume. Default: 90.
        If no unit is specified, the value is in %. Example: 50
        If a unit is specified, the value is in bytes. Supported units are B, K, M, G, T, P, E, Z, Y. Example: 250M

    **min_mem**
        The minimum memory one process of this watcher should consume. Default: None (no minimum).
        If no unit is specified, the value is in %. Example: 50
        If a unit is specified, the value is in bytes. Supported units are B, K, M, G, T, P, E, Z, Y. Example: 250M

    **health_threshold**
        The health is the average of cpu and memory (in %) the watchers processes are allowed to consume (in %). Default: 75

    **max_count**
        How often these limits (each one is counted separately) are allowed to be exceeded before a restart will be triggered. Default: 3



Example:

.. code-block:: ini

    [circus]
    ; ...

    [watcher:program]
    cmd = sleep 120

    [plugin:myplugin]
    use = circus.plugins.resource_watcher.ResourceWatcher
    watcher = program
    min_cpu = 10
    max_cpu = 70
    min_mem = 0
    max_mem = 20

Watchdog
========

    Plugin that binds an udp socket and wait for watchdog messages.
    For "watchdoged" processes, the watchdog will kill them if they
    don't send a heartbeat in a certain period of time materialized by
    loop_rate * max_count. (circus will automatically restart the missing
    processes in the watcher)

    Each monitored process should send udp message at least at the loop_rate.
    The udp message format is a line of text, decoded using **msg_regex**
    parameter.
    The heartbeat message MUST at least contain the pid of the process sending
    the message.

    The list of monitored watchers are determined by the parameter
    **watchers_regex** in the configuration.


    Configuration parameters:

    **use**
      set to ``circus.plugins.watchdog.WatchDog``

    **loop_rate**
        watchdog loop rate in seconds. At each loop, WatchDog
        will looks for "dead" processes.

    **watchers_regex**
        regex for matching watcher names that should be
        monitored by the watchdog (default: ``.*`` all watchers are monitored)

    **msg_regex**
        regex for decoding the received heartbeat
        message in udp (default: ``^(?P<pid>.*);(?P<timestamp>.*)$``)
        the default format is a simple text message: ``pid;timestamp``

    **max_count**
        max number of passed loop without receiving
        any heartbeat before restarting process (default: 3)

    **ip**
        ip the watchdog will bind on (default: 127.0.0.1)

    **port**
        port the watchdog will bind on (default: 1664)


Flapping
========

    When a worker restarts too often, we say that it is *flapping*.  This
    plugin keeps track of worker restarts and stops the corresponding watcher
    in case it is flapping. This plugin may be used to automatically stop
    workers that get constantly restarted because they're not working
    properly.

    **use**
      set to ``circus.plugins.flapping.Flapping``
    **attempts**
      the number of times a process can restart, within **window** seconds,
      before we consider it flapping (default: 2)
    **window**
      the time window in seconds to test for flapping.  If the process
      restarts more than **attempts** times within this time window, we
      consider it a flapping process.  (default: 1)
    **retry_in**
      time in seconds to wait until we try to start again a process that has
      been flapping. (default: 7)
    **max_retry**
      the number of times we attempt to start a process that has been
      flapping, before we abandon and stop the whole watcher. (default: 5) Set
      to -1 to disable max_retry and retry indefinitely.
    **active**
      define if the plugin is active or not (default: True).  If the global
      flag is set to False, the plugin is not started.

Options can be overriden in the watcher section using a ``flapping.``
prefix. For instance, here is how you would configure a specific ``max_retry`` value for nginx:

.. code-block:: ini

        [watcher:nginx]
        cmd = /path/to/nginx
        flapping.max_retry = 2

        [watcher:myscript]
        cmd = ./my_script.py

        ; ... other watchers

        [plugin:flapping]
        use = circus.plugins.flapping.Flapping
        max_retry = 5


CommandReloader
===============

    This plugin will restart watchers when their command file is modified. It
    works by checking the modification time and the path of the file pointed by
    the **cmd** option every **loop_rate** seconds. This may be useful while
    developing worker processes or even for hot code upgrade in production.

    **use**
      set to ``circus.plugins.command_reloader.CommandReloader``
    **loop_rate**
      the frequency the plugin should check for modification in seconds. Default: 1.
