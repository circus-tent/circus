.. _plugins:

Plugins
#######

Circus comes with a few pre-shipped plugins you can use easily. The configuration of them is as follows:

Statsd
======
    
    **use**
         set to 'circus.plugins.statsd.StatsdEmitter'

    **application_name**
        the name used to identify the bucket prefix to emit the stats to (it will be prefixed with "circus." and suffixed with ".watcher")

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
        set to 'circus.plugins.statsd.FullStats'

    **loop_rate**
        the frequency the plugin should ask for the stats in seconds. Default: 60.


RedisObserver
=============

    This services observers a redis process for you, publishes the information to statsd
    and offers to restart the service when it doesn't react in a given timeout. This
    plugin requires `redis-py <https://github.com/andymccurdy/redis-py>`_  to run.

    It has the same configuration as statsd and adds the following:

    **use**
        set to   'circus.plugins.redis_observer.RedisObserver'

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

    This services observers a http process for you by pinging a certain website
    regularly. Similar to the redis observer it offers to restart the service on an
    error. It requires `tornado <http://www.tornadoweb.org>`_  to run.

    It has the same configuration as statsd and adds the following:

    **use**
        set to 'circus.plugins.http_observer.HttpObserver'

    **loop_rate**
        the frequency the plugin should ask for the stats in seconds. Default: 60.

    **check_url**
        the url to check for. Default: "http://localhost/"

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
        set to 'circus.plugins.resource_watcher.ResourceWatcher'

    **loop_rate**
        the frequency the plugin should ask for the stats in seconds. Default: 60.

    **service**
        the service (read: watcher) this resource watcher should be looking after

    **max_cpu**
        The maximum cpu one process is allowed to consume (in %). Default: 90

    **max_mem**
        The amount of memory one process of this watcher is allowed to consume (in %). Default: 90

    **health_threshold**
        The health is the average of cpu and memory (in %) the watchers processes are allowed to consume (in %). Default: 75

    **max_count**
        How often these limits (each one is counted separately) are allowed to be exceeded before a restart will be triggered. Default: 3

