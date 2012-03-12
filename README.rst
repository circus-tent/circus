======
Circus
======

Circus is a program that runs and watches several processes.

Circus can be used as a library or through the command line.

For more information about the motivation for this project, see `this blog post <http://ziade.org/2012/02/24/circus-a-process-controller/>`_.


Library
-------

Circus provides high-level Classes and functions that will let you run
processes. For example, if you just want to run 4 workers forever, you
can write::

    from circus import get_trainer

    trainer = get_trainer("myprogram", 3)
    try:
        trainer.start()
    finally:
        trainer.stop()

This snippet will run 3 *myprogram* processes and watch them for you.

See http://packages.python.org/circus for a full Library documentation.


Command-Line Interface
-----------------------

Circus provides a command line script that can be used to run one or several
types of processes.

It's an ini-style like file. Example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555

    [show:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    num_flies = 5

The file is then run using *circusd*::

    $ circusd example.ini

There's also a *circusctl* command line tool to query Circus to perform
actions like adding or removing workers, or getting back some statistics.

See http://packages.python.org/circus for a full documentation on the
configuration file and the commands options.


Contributions and Feedback
--------------------------

You can reach us for any feedback, bug report, or to contribute, at
https://github.com/mozilla-services/circus
