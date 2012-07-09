.. _cli:

Using Circus from the command line
##################################

Circus can be used as a tool which manages your processes for you, whithout
needing from you any knownledge about the Python language. The interface is
provided via simple command line scripts and configuration files.

Running Circus
--------------

Circus provides a command-line script call **circusd** that can be used
to manage one or more :term:`watchers`. Each watcher can have one or more
running :term:`processes`.

Circus' command-line tool is configurable using an ini-style
configuration file. Here is a minimal example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555

    [watcher:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    numprocesses = 5

    [watcher:anotherprogram]
    cmd = another_program
    numprocesses = 2


The file is then run using *circusd*::

    $ circusd example.ini

Besides processes, Circus can also bind sockets. Since every process managed by
Circus is a child of the main Circus daemon, that means any program that's
controlled by Circus can use those sockets.

Running a socket is as simple as adding a *socket* section in the config file::

    [socket:mysocket]
    host = localhost
    port = 8080


To learn more about sockets, see :ref:`sockets`.

To understand why it's a killer feature, read :ref:`whycircussockets`.

Controlling Circus
------------------

Circus provides two command-line tools to manage your running daemon:

- *circusctl*, a management console you can use it to perform
  actions such as adding or removing :term:`workers`

- *circus-top*, a top-like console you can use to display the memory and
  cpu usage of your running Circus.

Circus also offers a small web application that can connect to a
running Circus daemon and let you monitor and interact with it.

To learn more about this feature, see :ref:`circushttpd`


circus-top
==========

*circus-top* is a top-like console you can run to watch
live your running Circus system. It will display the CPU, Memory
usage and socket hits if you have some.


Example of output::

    -----------------------------------------------------------------------
    circusd-stats
     PID                 CPU (%)             MEMORY (%)
    14252                 0.8                 0.4
                          0.8 (avg)           0.4 (sum)

    dummy
     PID                 CPU (%)             MEMORY (%)
    14257                 78.6                0.1
    14256                 76.6                0.1
    14258                 74.3                0.1
    14260                 71.4                0.1
    14259                 70.7                0.1
                          74.32 (avg)         0.5 (sum)

    ----------------------------------------------------------------------


*circus-top* is a read-only console. If you want to interact with the system,
use *circusctl*.

circusctl
=========

*circusctl* can be used to run any command listed in :ref:`commands` . For
example, you can get a list of all the watchers, you can do ::

    $ circusctl list
