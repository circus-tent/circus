Configuration
-------------

Circus can be configured using an ini-style configuration file.

Example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555
    pubsub_endpoint = tcp://127.0.0.1:5556


    [watcher:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    numprocesses = 5

    # will push in test.log the stream every 300 ms
    stdout_stream.class = FileStream
    stdout_stream.filename = test.log
    stdout_stream.refresh_time = 0.3


circus (single section)
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
        List of config files to include. (default: None)
    **include_dir**
        List of config directories. All files matching `*.ini` under each
        directory will be included. (default: None)
    **stream_backend**
        Defines the type of backend to use for the streaming. Possible
        values are **thread** or **gevent**. (default: thread)


.. note::

   If you use the gevent backend for **stream_backend**, you need to install the
   forked version of gevent_zmq that's located at
   https://github.com/tarekziade/gevent-zeromq because it contains a fix that has
   not made it upstream yet.


watcher:NAME (as many sections as you want)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **NAME**
        The name of the watcher. This name is used in **circusctl**
    **cmd**
        The executable program to run.
    **args**
        Command-line arguments to pass to the program. You can use the python
        format syntax here to build the parameters. Environment variables are
        available, as well as WID and the environment variables that you
        passed, if any, with the "env" parameter.
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
        The environment passed to the processes (default: None)
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

        Circus provides two classes you can use without prefix:

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
        Circus provides two classes you can use without prefix:

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

    **flapping_attempts**
        Number of times a process can restart before we start to
        detect the flapping. Defaults to 2.

    **within**
        The time window in seconds to test for flapping. If the
        process restarts more than **flapping_attempts**
        times, we consider it a flapping process. Defaults to 1.

    **retry_in**
        The time in seconds to wait until we try to start a process
        that has been flapping. Defaults to 7.

    **max_retry**
        The number of times we attempt to start a process, before
        we abandon and stop the whole watcher. Defaults to 5.

    **priority**
        Integer that defines a priority for the watcher. When the
        Arbiter do some operations on all watchers, it will sort them
        with this field, from the bigger number to the smallest.
        Defaults to 0.
