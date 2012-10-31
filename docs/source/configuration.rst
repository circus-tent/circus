Configuration
-------------

Circus can be configured using an ini-style configuration file.

Example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555
    pubsub_endpoint = tcp://127.0.0.1:5556
    include = /path/to/configs/*.enabled.ini

    [watcher:myprogram]
    cmd = python
    args = -u myprogram.py $(WID) $(ENV.VAR)
    warmup_delay = 0
    numprocesses = 5

    # hook
    hooks.before_start = my.hooks.control_redis

    # will push in test.log the stream every 300 ms
    stdout_stream.class = FileStream
    stdout_stream.filename = test.log
    stdout_stream.refresh_time = 0.3

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
~~~~~~~~~~~~~~~~~~~~~~~
    **endpoint**
        The ZMQ socket used to manage Circus via **circusctl**.
        (default: *tcp://127.0.0.1:5555*)
    **pubsub_endpoint**
        The ZMQ PUB/SUB socket receiving publications of events.
        (default: *tcp://127.0.0.1:5556*)
    **stats_endpoint**
        The ZMQ PUB/SUB socket receiving publications of stats.
        If not configured, this feature is deactivated.
        (default: *tcp://127.0.0.1:5557*)
    **check_delay**
        The polling interval in seconds for the ZMQ socket. (default: 5)
    **include**
        List of config files to include. (default: None). You can use wildcards
        (`*`) to include particular schemes for your files.
    **include_dir**
        List of config directories. All files matching `*.ini` under each
        directory will be included. (default: None)
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
    **debug**
        If set to True, all Circus stout/stderr daemons are redirected to circusd
        stdout/stderr (default: False)
    **respawn**
        If set to False, the processes handled by a watcher will not be
        respawned automatically. (default: True)

.. note::

   If you use the gevent backend for **stream_backend**, you need to install the
   forked version of gevent_zmq that's located at
   https://github.com/tarekziade/gevent-zeromq because it contains a fix that has
   not made it upstream yet.


watcher:NAME - as many sections as you want
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **NAME**
        The name of the watcher. This name is used in **circusctl**
    **cmd**
        The executable program to run.
    **args**
        Command-line arguments to pass to the program. You can use the python
        format syntax here to build the parameters. Environment variables are
        available, as well as the worker id and the environment variables that
        you passed, if any, with the "env" parameter. See
        :ref:`formating_cmd` for more information on this.
    **shell**
        If True, the processes are run in the shell (default: False)
    **working_dir**
        The working dir for the processes (default: None)
    **uid**
        The user id or name the command should run with.
        (The current uid is the default).
    **gid**
        The group id or name the command should run
        with. (The current gid is the default).
    **env**
        The environment passed to the processes. Bash style environment
        variables are supported. For example, append '/usr/local/bin' to
        `PATH` with the config line 'env = PATH=$PATH:/usr/local/bin'
        (default: None)
    **copy_env**
        If set to true, the local environment variables will be copied and
        passed to the workers when spawning them. (Default: False)
    **copy_path**
        If set to true, **sys.path** is passed in the subprocess environ
        using *PYTHONPATH*. **copy_env** has to be true.
        (Default: False)
    **warmup_delay**
        The delay (in seconds) between running processes.
    **numprocesses**
        The number of processes to run for this watcher.
    **rlimit_LIMIT**
        Set resource limit LIMIT for the watched processes. The
        config name should match the RLIMIT_* constants (not case
        sensitive) listed in the `Python resource module reference
        <http://docs.python.org/library/resource.html#resource-limits>`_.
        For example, the config line 'rlimit_nofile = 500' sets the maximum
        number of open files to 500.
    **stderr_stream.class**
        A fully qualified Python class name that will be instanciated, and
        will receive the **stderr** stream of all processes in its
        :func:`__call__` method.

        Circus provides three classes you can use without prefix:

        - :class:`FileStream`: writes in a file
        - :class:`QueueStream`: write in a memory Queue
        - :class:`StdoutStream`: writes in the stdout

    **stderr_stream.***
        All options starting with *stderr_stream.* other than *class* will
        be passed the constructor when creating an instance of the
        class defined in **stderr_stream.class**.
    **stdout_stream.class**
        A fully qualified Python class name that will be instanciated, and
        will receive the **stdout** stream of all processes in its
        :func:`__call__` method.
        Circus provides three classes you can use without prefix:

        - :class:`FileStream`: writes in a file
        - :class:`QueueStream`: write in a memory Queue
        - :class:`StdoutStream`: writes in the stdout

    **stdout_stream.***
        All options starting with *stdout_stream.* other than *class* will
        be passed the constructor when creating an instance of the
        class defined in **stdout_stream.class**.

    **send_hup**
        if True, a process reload will be done by sending the SIGHUP signal.
        Defaults to False.

    **max_retry**
        The number of times we attempt to start a process, before
        we abandon and stop the whole watcher. Defaults to 5.

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

    **hooks.***
        Available hooks: **before_start**, **after_start**, **before_stop**, **after_stop**

        Define callback functions that hook into the watcher startup/shutdown process.

        If the hook returns **False** and if the hook is one of
        **before_start** or **after_start**, the startup will be aborted.

        Notice that a hook that fails during the stopping process will not
        abort it.

        The callback definition can be followed by a boolean flag separated by a
        comma. When the flag is set to **true**, any error occuring in the
        hook will be ignored. If set to **false** (the default), the hook
        will return **False**.

        More on :ref:`hooks`.


socket:NAME - as many sections as you want
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
    **path**
        When provided a path to a file that will be used as a unix socket
        file. If a path is provided, **family** is forced to AF_UNIX and
        **host** and **port** are ignored.


Once a socket is created, the *${circus.sockets.NAME}* string can be used in the
command (`cmd` or `args`) of a watcher. Circus will replace it by the FD value. The watcher must also
have `use_sockets` set to `True` otherwise the socket will have been closed and
you will get errors when the watcher tries to use it.

Example::

    [watcher:webworker]
    cmd = chaussette --fd $(circus.sockets.webapp) chaussette.util.bench_app
    use_sockets = True

    [socket:webapp]
    host = 127.0.0.1
    port = 8888


plugin:NAME - as many sections as you want
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **use**
        The fully qualified name that points to the plugin class.
    **anything else**
        Every other key found in the section is passed to the
        plugin constructor in the **config** mapping.

Circus comes with a few pre-shipped :ref:`plugins <plugins>` but you can also extend them easily by :ref:`developing your own <develop_plugins>`.


.. _formating_cmd:

Formating the commands and arguments with dynamic variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
