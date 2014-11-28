.. _papa:

Papa Process Kernel
###################

One problem common to process managers is that you cannot restart the process
manager without restarting all of the processes it manages. This makes it
difficult to deploy a new version of Circus or new versions of any of the
libraries on which it depends.

If you are on a Unix-type system, Circus can use the Papa process kernel.
When used, Papa will create a long-lived daemon that will serve as the host for
any processes and sockets you create with it. If circus is shutdown, Papa will
maintain everything it is hosting.


Setup
=====

Start by installing the `papa` and `setproctitle` modules::

    pip install papa
    pip install setproctitle

The `setproctitle` module is optional. It will be used if present to rename the
Papa daemon for `top` and `ps` to something like "papa daemon from circusd".
If you do not install the `setproctitle` module, that title will be the command
line of the process that launched it. Very confusing.

Once Papa is installed, add `use_papa=true` to your critical processes and
sockets. Generally you want to house all of the processes of your stack in
Papa, and none of the Circus support processes such as the flapping and stats
plugins.

.. code-block:: ini

    [circus]
    loglevel = info

    [watcher:nginx]
    cmd = /usr/local/nginx/sbin/nginx -p /Users/scottmax/Source/service-framework/Common/conf/nginx -c /Users/scottmax/Source/service-framework/Common/conf/nginx/nginx.conf
    warmup_delay = 3
    graceful_timeout = 10
    max_retry = 5
    singleton = true
    send_hup = true
    stop_signal = QUIT
    stdout_stream.class = FileStream
    stdout_stream.filename = /var/logs/web-server.log
    stdout_stream.max_bytes = 10000000
    stdout_stream.backup_count = 10
    stderr_stream.class = FileStream
    stderr_stream.filename = /var/logs/web-server-error.log
    stderr_stream.max_bytes = 1000000
    stderr_stream.backup_count = 10
    active = true
    use_papa = true

    [watcher:logger]
    cmd = /my_service/env/bin/python logger.py run
    working_dir = /my_service
    graceful_timeout = 10
    singleton = true
    stop_signal = INT
    stdout_stream.class = FileStream
    stdout_stream.filename = /var/logs/logger.log
    stdout_stream.max_bytes = 10000000
    stdout_stream.backup_count = 10
    stderr_stream.class = FileStream
    stderr_stream.filename = /var/logs/logger.log
    stderr_stream.max_bytes = 1000000
    stderr_stream.backup_count = 10
    priority = 50
    use_papa = true

    [watcher:web_app]
    cmd = /my_service/env/bin/uwsgi --ini uwsgi-live.ini --socket fd://$(circus.sockets.web) --stats 127.0.0.1:809$(circus.wid)
    working_dir = /my_service/web_app
    graceful_timeout=10
    stop_signal = QUIT
    use_sockets = True
    stdout_stream.class = FileStream
    stdout_stream.filename = /var/logs/web_app.log
    stdout_stream.max_bytes = 10000000
    stdout_stream.backup_count = 10
    stderr_stream.class = FileStream
    stderr_stream.filename = /var/logs/web_app.log
    stderr_stream.max_bytes = 1000000
    stderr_stream.backup_count = 10
    hooks.after_spawn = examples.uwsgi_lossless_reload.children_started
    hooks.before_signal = examples.uwsgi_lossless_reload.clean_stop
    hooks.extended_stats = examples.uwsgi_lossless_reload.extended_stats
    priority = 40
    use_papa = true

    [socket:web]
    path = /my_service/sock/uwsgi
    use_papa = true

    [plugin:flapping]
    use = circus.plugins.flapping.Flapping
    window = 10
    priority = 1000


.. note::

    If the Papa processes use any sockets, those sockets must also use papa.


Design Goal
===========

Papa is designed to be very minimalist in features and requirements. It does:

* Start and stop sockets
* Provide a key/value store
* Start processes and return stdout, stderr and the exit code

It does not:

* Restart processes
* Provide a way to stop processes
* Provide any information about processes other than whether or not they
  are still running

Papa requires no third-party libraries so it can run on just the standard
Python library. It can make use of the `setproctitle` package but that is only
used for making the title prettier for `ps` and `top` and is not essential.

The functionality has been kept to a minimum so that you should never need to
restart the Papa daemon. As much of the functionality has been pushed to the
client library as possible. That way you should be able to deploy a new copy
of Papa for new client features without needing to restart the Papa daemon.
Papa is meant to be a pillar of stability in a changing sea of 3rd party
libraries.


Operation
=========

Most things remain unchanged whether you use Papa or not. You can still start
and stop processes. You can still get status and stats for processes. The main
thing that changes is that when you do `circusctl quit`, all of the Papa
processes are left running. When you start **circusd** back up, those processes
are recovered.

.. note::

    When processes are recovered, `before_start` and `before_spawn` hooks are
    skipped.


Logging
=======

While Circus is shut down, Papa will store up to 2M of output per process. Then
it will start dumping the oldest data. When you restart Circus, this cached
output will be quickly retrieved and sent to the output streams. Papa requires
that receipt of output be acknowledged, so you should not lose any output during
a shutdown.

Not only that, but Papa saves the timestamp of the output. Circus has been
enhanced to take advantage of timestamp data if present. So if you are writing
the output to log files or somewhere, your timestamps should all be correct.


Problems
========

If you use the `incr` or `decr` command to change the process count for a
watcher, this will be reset to the level specified in the INI file when
**circusd** is restarted.

Also, I have experienced problems with the combination of `copy_env` and
`virtualenv`. You may note that the INI sample above circumvents this issue
with explicit paths.

Telnet Interface
================

Papa has a basic command-line interface that you can access through telnet::

    telnet localhost 20202
    help

