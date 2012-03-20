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
    num_flies = 5

circus
~~~~~~
    **endpoint**
        The endpoint to which the ZMQ socket will be bound.
    **check_delay**
        The polling interval for the ZMQ socket.


watcher
~~~~~~~
    **cmd**
        The executable program to run.
    **args**
        Command-line arguments to pass to the program
    **warmup_delay**
        The delay (in seconds) between running flies.
    **num_flies**
        The number of flies to run for this watcher.
