.. _troubleshooting:

Troubleshooting
---------------

By default, `circusd` keeps its logging to `stdout` rather
sparse. This lack of output can make things hard to troubleshoot when
processes seem to be having trouble starting.

To increase the logging `circusd` provides, try increasing the log
level. To see the available log levels just use the `--help` flag. ::

    $ circus --log-level debug test.ini

One word of warning. If a process is flapping and the debug log level
is turned on, you will see messages for each start attempt. It might
be helpful to configure the app that is flapping to use a
`warmup_delay` to slow down the messages to a manageable pace. ::

    [watcher:webapp]
    cmd = python -m myapp.wsgi
    warmup_delay = 5

By default, `stdout` and `stderr` are captured by the `circusd`
process. If you are testing your config and want to see the output in
line with the circusd output, you can configure your watcher to use
the `StdoutStream` class. ::

    [watcher:webapp]
    cmd = python -m myapp.wsgi
    stdout_stream.class = StdoutStream
    stderr_stream.class = StdoutStream

If your application is producing a traceback or error when it is
trying to start up you should be able to see it in the output.
