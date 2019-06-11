.. _configuration:

Configuration
#############

Circus can be configured using an ini-style configuration file.

Example:

.. code-block:: ini

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555
    pubsub_endpoint = tcp://127.0.0.1:5556
    include = \*.more.config.ini
    umask = 002

    [watcher:myprogram]
    cmd = python
    args = -u myprogram.py $(circus.wid) $(CIRCUS.ENV.VAR)
    warmup_delay = 0
    numprocesses = 5

    # hook
    hooks.before_start = my.hooks.control_redis

    # will push in test.log the stream every 300 ms
    stdout_stream.class = FileStream
    stdout_stream.filename = test.log

    # optionally rotate the log file when it reaches 1 gb
    # and save 5 copied of rotated files
    stdout_stream.max_bytes = 1073741824
    stdout_stream.backup_count = 5

    [env:myprogram]
    PATH = $PATH:/bin
    CAKE = lie

    [plugin:statsd]
    use = circus.plugins.statsd.StatsdEmitter
    host = localhost
    port = 8125
    sample_rate = 1.0
    application_name = example

    [socket:web]
    host = localhost
    port = 8080


circus - single section
=======================
    **endpoint**
        The ZMQ socket used to manage Circus via **circusctl**.
        (default: *tcp://127.0.0.1:5555*)
    **endpoint_owner**
        If set to a system username and the endpoint is an ipc socket like
        *ipc://var/run/circusd.sock*, then ownership of the socket file will
        be changed to that user at startup. For more details, see :ref:`security`.
        (default: None)
    **pubsub_endpoint**
        The ZMQ PUB/SUB socket receiving publications of events.
        (default: *tcp://127.0.0.1:5556*)
    **papa_endpoint**
        If using :ref:`papa`, you can specify the endpoint, such as
        *ipc://var/run/circusd.sock*.
        (default: *tcp://127.0.0.1:20202*)
    **statsd**
        If set to True, Circus runs the circusd-stats daemon. (default: False)
    **stats_endpoint**
        The ZMQ PUB/SUB socket receiving publications of stats.
        (default: *tcp://127.0.0.1:5557*)
    **statsd_close_outputs**
        If True sends the circusd-stats stdout/stderr to ``/dev/null``.
        (default: False)
    **check_delay**
        The polling interval in seconds for the ZMQ socket. (default: 5)
    **include**
        List of config files to include. You can use wildcards
        (`*`) to include particular schemes for your files. The paths are
        absolute or relative to the config file. (default: None)
    **include_dir**
        List of config directories. All files matching `*.ini` under each
        directory will be included. The paths are absolute or relative to the
        config file. (default: None)
    **stream_backend**
        Defines the type of backend to use for the streaming. Possible
        values are **thread** or **gevent**. (default: thread)
    **warmup_delay**
        The interval in seconds between two watchers start. Must be an int. (default: 0)
    **httpd**
        If set to True, Circus runs the circushttpd daemon. (default: False)
    **httpd_host**
        The host ran by the circushttpd daemon. (default: localhost)
    **httpd_port**
        The port ran by the circushttpd daemon. (default: 8080)
    **httpd_close_outputs**
        If True, sends the circushttpd stdout/stderr to ``/dev/null``.
        (default: False)
    **debug**
        If set to True, all Circus stout/stderr daemons are redirected to circusd
        stdout/stderr (default: False)
    **debug_gc**
        If set to True, circusd outputs additional log info from the garbage
        collector. This can be useful in tracking down memory leaks.
        (default: False)
    **pidfile**
        The file that must be used to keep the daemon pid.
    **umask**
        Value for umask. If not set, circusd will not attempt to modify umask.
    **loglevel**
        The loglevel that we want to see (default: INFO)
    **logoutput**
        The logoutput file where we want to log (default: ``-`` to log
        on stdout). You can log to a remote syslog by using the
        following syntax: ``syslog://host:port?facility`` where host
        is your syslog server, port is optional and facility is the
        syslog facility to use. If you wish to log to a local syslog
        you can use ``syslog:///path/to/syslog/socket?facility``
        instead.
    **loggerconfig**
        A path to an INI, JSON or YAML file to configure standard Python
        logging for the Arbiter.  The special value "default" uses the builtin
        logging configuration based on the optional loglevel and logoutput options.

        **Example YAML Configuration File**

    .. code-block:: yaml

            version: 1
            disable_existing_loggers: false
            formatters:
              simple:
                format: '%(asctime)s - %(name)s - [%(levelname)s] %(message)s'
            handlers:
              logfile:
                class: logging.FileHandler
                filename: logoutput.txt
                level: DEBUG
                formatter: simple
            loggers:
              circus:
                level: DEBUG
                handlers: [logfile]
                propagate: no
            root:
              level: DEBUG
              handlers: [logfile]

watcher:NAME - as many sections as you want
===========================================
    **NAME**
        The name of the watcher. This name is used in **circusctl**
    **cmd**
        The executable program to run.
    **args**
        Command-line arguments to pass to the program. You can use the python
        format syntax here to build the parameters. Environment variables are
        available, as well as the worker id and the environment variables that
        you passed, if any, with the "env" parameter. See
        :ref:`formatting_cmd` for more information on this.
    **shell**
        If True, the processes are run in the shell (default: False)
    **shell_args**
        Command-line arguments to pass to the shell command when **shell** is
        True. Works only for \*nix system (default: None)
    **working_dir**
        The working dir for the processes (default: None)
    **uid**
        The user id or name the command should run with.
        (The current uid is the default).
    **gid**
        The group id or name the command should run
        with. (The current gid is the default).
    **copy_env**
        If set to true, the local environment variables will be copied and
        passed to the workers when spawning them. (Default: False)
    **copy_path**
        If set to true, **sys.path** is passed in the subprocess environ
        using *PYTHONPATH*. **copy_env** has to be true.
        (Default: False)
    **warmup_delay**
        The delay (in seconds) between running processes.
    **autostart**
        If set to false, the watcher will not be started automatically
        when the arbiter starts. The watcher can be started explicitly
        (example: `circusctrl start myprogram`). (Default: True)
    **numprocesses**
        The number of processes to run for this watcher.
    **rlimit_LIMIT**
        Set resource limit LIMIT for the watched processes. The
        config name should match the RLIMIT_* constants (not case
        sensitive) listed in the `Python resource module reference
        <http://docs.python.org/library/resource.html#resource-limits>`_.
        For example, the config line 'rlimit_nofile = 500' sets the maximum
        number of open files to 500. To set a limit value to RLIM_INFINITY,
        do not set a value, like this config line: 'rlimit_nofile = '.
    **stderr_stream.class**
        A fully qualified Python class name that will be instanciated, and
        will receive the **stderr** stream of all processes in its
        :func:`__call__` method.

        Circus provides some stream classes you can use without prefix:

        - :class:`FileStream`: writes in a file and can do automatic log rotation
        - :class:`WatchedFileStream`: writes in a file and relies on external log rotation
        - :class:`TimedRotatingFileStream`: writes in a file and can do rotate at certain timed intervals.
        - :class:`QueueStream`: write in a memory Queue
        - :class:`StdoutStream`: writes in the stdout
        - :class:`FancyStdoutStream`: writes colored output with time prefixes in the stdout

    **stderr_stream.***
        All options starting with *stderr_stream.* other than *class* will
        be passed the constructor when creating an instance of the
        class defined in **stderr_stream.class**.
    **stdout_stream.class**
        A fully qualified Python class name that will be instanciated, and
        will receive the **stdout** stream of all processes in its
        :func:`__call__` method.

        Circus provides some stream classes you can use without prefix:

        - :class:`FileStream`: writes in a file and can do automatic log rotation
        - :class:`WatchedFileStream`: writes in a file and relies on external log rotation
        - :class:`TimedRotatingFileStream`: writes in a file and can do rotate at certain timed intervals.
        - :class:`QueueStream`: write in a memory Queue
        - :class:`StdoutStream`: writes in the stdout
        - :class:`FancyStdoutStream`: writes colored output with time prefixes in the stdout

    **stdout_stream.***
        All options starting with *stdout_stream.* other than *class* will
        be passed the constructor when creating an instance of the
        class defined in **stdout_stream.class**.

    **stdin_socket**
        If not None, the socket with matching name is placed at file descriptor 0 (stdin)
	of the processes. (Default: None)

    **close_child_stdin**
        If set to True, the stdin stream of each process will be sent to
        ``/dev/null`` after the fork. Defaults to True.

        The primary use case for this option is debugging. Set it to False and
        Circus will leave *stdin* open for the watcher processes. This allows
        interactive debugger sessions to be attached to them. In case of a
        Python program, one could insert a Pdb call (``import pdb;
        pdb.set_trace()``) somewhere in the code and acquire its shell to
        debug the program.

        If debugging a process is not expected, leave this option in its default
        value, True. This will prevent, for example, that the process hangs
        indefinitely waiting on input which could never come, especially if
        Circus runs as a daemon.

    **close_child_stdout**
        If set to True, the stdout stream of each process will be sent to
        ``/dev/null`` after the fork. Defaults to False.

    **close_child_stderr**
        If set to True, the stderr stream of each process will be sent to
        ``/dev/null`` after the fork. Defaults to False.

    **send_hup**
        If True, a process reload will be done by sending the SIGHUP signal.
        Defaults to False.

    **stop_signal**
        The signal to send when stopping the process. Can be specified as a
        number or a signal name. Signal names are case-insensitive and can
        include 'SIG' or not. So valid examples include `quit`, `INT`,
        `SIGTERM` and `3`.
        Defaults to SIGTERM.

    **stop_children**
        When sending the *stop_signal*, send it to the children as well.
        Defaults to False.

    **max_retry**
        The number of times we attempt to start a process, before
        we abandon and stop the whole watcher. Defaults to 5.
        Set to -1 to disable max_retry and retry indefinitely.

.. _graceful_timeout:

    **graceful_timeout**
        The number of seconds to wait for a process to terminate gracefully
        before killing it.

        When stopping a process, we first send it a *stop_signal*. A worker
        may catch this signal to perform clean up operations before exiting.
        If the worker is still active after graceful_timeout seconds, we send
        it a SIGKILL signal.  It is not possible to catch SIGKILL signals so
        the worker will stop.

        Defaults to 30s.

    **priority**
        Integer that defines a priority for the watcher. When the
        Arbiter do some operations on all watchers, it will sort them
        with this field, from the bigger number to the smallest.
        Defaults to 0.

    **singleton**
        If set to True, this watcher will have at the most one process.
        Defaults to False.

    **use_sockets**
        If set to True, this watcher will be able to access defined sockets
        via their file descriptors. If False, all parent fds are closed
        when the child process is forked. Defaults to False.

    **max_age**
        If set then the process will be restarted sometime after max_age
        seconds. This is useful when processes deal with pool of connectors:
        restarting processes improves the load balancing. Defaults to being
        disabled.

    **max_age_variance**
        If max_age is set then the process will live between max_age and
        max_age + random(0, max_age_variance) seconds. This avoids restarting
        all processes for a watcher at once. Defaults to 30 seconds.

    **on_demand**
        If set to True, the processes will be started only after the first
        connection to one of the configured sockets (see below). If a restart
        is needed, it will be only triggered at the next socket event.

    **hooks.***
        Available hooks: **before_start**, **after_start**,
        **before_spawn**, **after_spawn**,
        **before_stop**, **after_stop**,
        **before_signal**, **after_signal**,
        **before_reap**, **after_reap**,
        **extended_stats**

        Define callback functions that hook into the watcher startup/shutdown process.

        If the hook returns **False** and if the hook is one of
        **before_start**, **before_spawn**, **after_start** or **after_spawn**,
        the startup will be aborted.

        If the hook is **before_signal** and returns **False**, then the
        corresponding signal will not be sent (except SIGKILL which is always
        sent)

        Notice that a hook that fails during the stopping process will not
        abort it.

        The callback definition can be followed by a boolean flag separated by a
        comma. When the flag is set to **true**, any error occuring in the
        hook will be ignored. If set to **false** (the default), the hook
        will return **False**.

        More on :ref:`hooks`.

    **virtualenv**
        When provided, points to the root of a Virtualenv directory. The
        watcher will scan the local **site-packages** and loads its content
        into the execution environment. Must be used with **copy_env** set
        to True. Defaults to None.

    **virtualenv_py_ver**
        Specifies the python version of the virtualenv (e.g "3.3").
        It's usefull if circus run with another python version (e.g "2.7")
        The watcher will scan the local **site-packages** of the specified
        python version and load its content into the execution
        environment. Must be used with **virtualenv**. Defaults to None.

    **respawn**
        If set to False, the processes handled by a watcher will not be
        respawned automatically. The processes can be manually respawned with
        the `start` command. (default: True)

    **use_papa**
        Set to true to use the :ref:`papa`.



socket:NAME - as many sections as you want
==========================================
    **host**
        The host of the socket. Defaults to 'localhost'
    **port**
        The port. Defaults to 8080.
    **family**
        The socket family. Can be 'AF_UNIX', 'AF_INET' or 'AF_INET6'.
        Defaults to 'AF_INET'.
    **type**
        The socket type. Can be 'SOCK_STREAM', 'SOCK_DGRAM', 'SOCK_RAW',
        'SOCK_RDM' or 'SOCK_SEQPACKET'. Defaults to 'SOCK_STREAM'.
    **interface**
        When provided a network interface name like 'eth0', binds the socket
        to that particular device so that only packets received from that
        particular interface are processed by the socket.
        This can be used for example to limit which device to bind when
        binding on IN_ADDR_ANY (0.0.0.0) or IN_ADDR_BROADCAST
        (255.255.255.255). Note that this only works for some socket types,
        particularly AF_INET sockets.
    **path**
        When provided a path to a file that will be used as a unix socket
        file. If a path is provided, **family** is forced to AF_UNIX and
        **host** and **port** are ignored.
    **umask**
        When provided, sets the umask that will be used to create an
        AF_UNIX socket. For example, `umask=000` will produce a socket with
        permission `777`.
    **replace**
        When creating Unix sockets ('AF_UNIX'), an existing file may indicate a
        problem so the default is to fail. Specify `True` to simply remove the
        old file if you are sure that the socket is managed only by Circus.
    **so_reuseport**
        If set to True and SO_REUSEPORT is available on target platform, circus
        will create and bind new SO_REUSEPORT socket(s) for every worker it starts
        which is a user of this socket(s).
    **blocking**
        If `True`, socket is set to blocking. If `False`, socket is set to non-blocking.
        (default: False)

    **use_papa**
        Set to true to use the :ref:`papa`.


Once a socket is created, the *${circus.sockets.NAME}* string can be used in the
command (`cmd` or `args`) of a watcher. Circus will replace it by the FD value. The watcher must also
have `use_sockets` set to `True` otherwise the socket will have been closed and
you will get errors when the watcher tries to use it.

Example:

.. code-block:: ini

    [watcher:webworker]
    cmd = chaussette --fd $(circus.sockets.webapp) chaussette.util.bench_app
    use_sockets = True

    [socket:webapp]
    host = 127.0.0.1
    port = 8888


plugin:NAME - as many sections as you want
==========================================
    **use**
        The fully qualified name that points to the plugin class.
    **anything else**
        Every other key found in the section is passed to the
        plugin constructor in the **config** mapping.

        You can use all the watcher options, since a plugin is
        started like a watcher.

Circus comes with a few pre-shipped :ref:`plugins <plugins>` but you can also extend them easily by :ref:`developing your own <develop_plugins>`.


env or env[:WATCHERS] - as many sections as you want
====================================================
    **anything**
        The name of an environment variable to assign value to.
        bash style environment substitutions are supported.
        for example, append /bin to `PATH` 'PATH = $PATH:/bin'

Section responsible for delivering environment variable to run processes.

Example:

.. code-block:: ini

    [watcher:worker1]
    cmd = ping 127.0.0.1

    [watcher:worker2]
    cmd = ping 127.0.0.1

    [env]
    CAKE = lie

The variable `CAKE` will propagated to all watchers defined in config file.

WATCHERS can be a comma separated list of watcher sections to apply this environment to.
if multiple env sections match a watcher, they will be combine in the order they appear in the configuration file.
later entries will take precedence.

Example:

.. code-block:: ini

    [watcher:worker1]
    cmd = ping 127.0.0.1

    [watcher:worker2]
    cmd = ping 127.0.0.1

    [env:worker1,worker2]
    PATH = /bin

    [env:worker1]
    PATH = $PATH

    [env:worker2]
    CAKE = lie

`worker1` will be run with PATH = $PATH (expanded from the environment circusd was run in)
`worker2` will be run with PATH = /bin and CAKE = lie

It's possible to use wildcards as well.

Example:

.. code-block:: ini

    [watcher:worker1]
    cmd = ping 127.0.0.1

    [watcher:worker2]
    cmd = ping 127.0.0.1

    [env:worker*]
    PATH = /bin


Both `worker1` and `worker2` will be run with PATH = /bin


Using environment variables
===========================

When writing your configuration file, you can use environment
variables defined in the *env* section or in *os.environ* itself.

You just have to use the *circus.env.* prefix.

Example:

.. code-block:: ini

    [watcher:worker1]
    cmd = $(circus.env.shell)

    [watcher:worker2]
    baz = $(circus.env.user)
    bar = $(circus.env.yeah)
    sup = $(circus.env.oh)

    [socket:socket1]
    port = $(circus.env.port)

    [plugin:plugin1]
    use = some.path
    parameter1 = $(circus.env.plugin_param)

    [env]
    yeah = boo

    [env:worker2]
    oh = ok

If a variable is defined in several places, the most specialized
value has precedence: a variable defined in *env:XXX* will override
a variable defined in *env*, which will override a variable
defined in *os.environ*.

environment substitutions can be used in any section of the configuration
in any section variable.


.. _formatting_cmd:

Formatting the commands and arguments with dynamic variables
============================================================

As you may have seen, it is possible to pass some information that are computed
dynamically when running the processes. Among other things, you can get the
worker id (WID) and all the options that are passed to the :class:`Process`.
Additionally, it is possible to access the options passed to the
:class:`Watcher` which instanciated the process.

.. note::

   The worker id is different from the process id. It's a unique value,
   starting at 1, which is only unique for the watcher.

For instance, if you want to access some variables that are contained in the
environment, you would need to do it with a setting like this::

    cmd = "make-me-a-coffee --sugar $(CIRCUS.ENV.SUGAR_AMOUNT)"

This works with both `cmd` and `args`.

**Important**:

- All variables are prefixed with `circus.`
- The replacement is case insensitive.

Stream configuration
====================

Simple stream class like `QueueStream` and `StdoutStream` don't have
specific attributes but some other stream class may have some:


FileStream
::::::::::

    **filename**
        The file path where log will be written.

    **time_format**
        The strftime format that will be used to prefix each time with a timestamp.
        By default they will be not prefixed.

        i.e: %Y-%m-%d %H:%M:%S

    **max_bytes**
        The max size of the log file before a new file is started.
        If not provided, the file is not rolled over.

    **backup_count**
        The number of log files that will be kept
        By default backup_count is null.


.. note::

    Rollover occurs whenever the current log file is nearly max_bytes in
    length. If backup_count is >= 1, the system will successively create
    new files with the same pathname as the base file, but with extensions
    ".1", ".2" etc. appended to it. For example, with a backup_count of 5
    and a base file name of "app.log", you would get "app.log",
    "app.log.1", "app.log.2", ... through to "app.log.5". The file being
    written to is always "app.log" - when it gets filled up, it is closed
    and renamed to "app.log.1", and if files "app.log.1", "app.log.2" etc.
    exist, then they are renamed to "app.log.2", "app.log.3" etc.
    respectively.

Example:

.. code-block:: ini

    [watcher:myprogram]
    cmd = python -m myapp.server

    stdout_stream.class = FileStream
    stdout_stream.filename = test.log
    stdout_stream.time_format = %Y-%m-%d %H:%M:%S
    stdout_stream.max_bytes = 1073741824
    stdout_stream.backup_count = 5


WatchedFileStream
:::::::::::::::::

    **filename**
        The file path where log will be written.

    **time_format**
        The strftime format that will be used to prefix each time with a timestamp.
        By default they will be not prefixed.

        i.e: %Y-%m-%d %H:%M:%S

.. note::

    WatchedFileStream relies on an external log rotation tool to ensure that
    log files don't become too big. The output file will be monitored and if
    it is ever deleted or moved by the external log rotation tool, then the
    output file handle will be automatically reloaded.

Example:

.. code-block:: ini

    [watcher:myprogram]
    cmd = python -m myapp.server

    stdout_stream.class = WatchedFileStream
    stdout_stream.filename = test.log
    stdout_stream.time_format = %Y-%m-%d %H:%M:%S


TimedRotatingFileStream
:::::::::::::::::::::::

    **filename**
        The file path where log will be written.

    **backup_count**
        The number of log files that will be kept By default backup_count is null.

    **time_format**
        The strftime format that will be used to prefix each time with a timestamp.
        By default they will be not prefixed.

        i.e: %Y-%m-%d %H:%M:%S

    **rotate_when**
        The type of interval.
        The list of possible values is below. Note that they are not case sensitive.

        .. csv-table::
            :header: Value, Type of interval
            :widths: 5, 5

            'S', Seconds
            'M', Minutes
            'H', Hours
            'D', Days
            'W0'-'W6', Weekday (0=Monday)
            'midnight', Roll over at midnight

    **rotate_interval**
        The rollover interval.

.. note::

    TimedRotatingFileStream rotates logfiles at certain timed intervals.
    Rollover interval is determined by a  combination of rotate_when and rotate_interval.

Example:

.. code-block:: ini

    [watcher:myprogram]
    cmd = python -m myapp.server

    stdout_stream.class = TimedRotatingFileStream
    stdout_stream.filename = test.log
    stdout_stream.time_format = %Y-%m-%d %H:%M:%S
    stdout_stream.utc = True
    stdout_stream.rotate_when = H
    stdout_stream.rotate_interval = 1


FancyStdoutStream
:::::::::::::::::

    **color**
        The name of an ascii color:
            - red
            - green
            - yellow
            - blue
            - magenta
            - cyan
            - white

    **time_format**
        The strftime format that each line will be prefixed with.

        Default to: %Y-%m-%d %H:%M:%S

Example:

.. code-block:: ini

    [watcher:myprogram]
    cmd = python -m myapp.server
    stdout_stream.class = FancyStdoutStream
    stdout_stream.color = green
    stdout_stream.time_format = %Y/%m/%d | %H:%M:%S
