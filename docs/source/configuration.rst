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
    **check_delay**
        The polling interval in seconds for the ZMQ socket. (default: 5)
    **include**
        List of config files to include. (defaults: None)
    **include_dir**
        List of config directories. All files matching `*.ini` under each
        directory will be included. (defaults: None)


watcher:NAME (as many sections as you want)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **NAME**
        The name of the watcher. This name is used for example in **circusctl**
    **cmd**
        The executable program to run.
    **args**
        Command-line arguments to pass to the program
    **shell**
        If True, the flies are run in the shell (default: False)
    **working_dir**
        The working dir for the processes (default: None)
    **uid**
        The user id used to run the flies (default: None)
    **gid**
        The group id used to run the flies (default: None)
    **env**
        The environment passed to the flies (default: None)
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
        will receive the **stderr** stream of all workers in its
        :func:`__call__` method.

        Circus provides two classes you can use without prefix:
        - :class:`FileStream`: writes in a file
        - :class:`QueueStream`: write in a memory Queue
    **stderr_stream.***
        All options starting with *stderr_stream.* other than *class* will
        be passed the constructor when creating an instance of the
        class defined in **stderr_stream.class**.
    **stdout_stream.class**
        A fully qualified Python class name that will be instanciated, and
        will receive the **stdout** stream of all workers in its
        :func:`__call__` method.
        Circus provides two classes you can use without prefix:
        - :class:`FileStream`: writes in a file
        - :class:`QueueStream`: write in a memory Queue
    **stdout_stream.***
        All options starting with *stdout_stream.* other than *class* will
        be passed the constructor when creating an instance of the
        class defined in **stdout_stream.class**.
