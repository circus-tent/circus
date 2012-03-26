Configuration
-------------

Circus can be configured using an ini-style configuration file.

Example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555

    [watcher:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    numprocesses = 5

circus (single section)
~~~~~~~~~~~~~~~~~~~~~~~
    **endpoint**
        The endpoint to which the ZMQ socket will be bound.
    **check_delay**
        The polling interval for the ZMQ socket.
    **include**
        List of config files to include.
    **include_dir**
        List of config directories. All files matching `*.ini` under each
        directory will be included.


watcher:NAME (as many sections as you want)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **NAME**
        The name of the watcher. This name is used for example in **circusctl**
    **cmd**
        The executable program to run.
    **args**
        Command-line arguments to pass to the program
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
