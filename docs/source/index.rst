Circus: A Process & Socket Manager
##################################

.. image:: circus-medium.png
   :align: right

Circus is a Python program which can be used to monitor and control processes and sockets.

Circus can be driven via a command-line interface, a web interface or programmatically through
its python API.

To install it and try its features check out the :ref:`examples`, or read the rest of this page
for a quick introduction.


Running a Circus Daemon
-----------------------


Circus provides a command-line script call **circusd** that can be used
to manage :term:`processes` organized in one or more :term:`watchers`.

Circus' command-line tool is configurable using an ini-style
configuration file.

Here's a very minimal example:

.. code-block:: ini

    [watcher:program]
    cmd = python myprogram.py
    numprocesses = 5

    [watcher:anotherprogram]
    cmd = another_program
    numprocesses = 2


The file is then passed to *circusd*::

    $ circusd example.ini


Besides processes, Circus can also bind sockets. Since every process managed by
Circus is a child of the main Circus daemon, that means any program that's
controlled by Circus can use those sockets.

Running a socket is as simple as adding a *socket* section in the config file:

.. code-block:: ini

    [socket:mysocket]
    host = localhost
    port = 8080

To learn more about sockets, see :ref:`sockets`.

To understand why it's a killer feature, read :ref:`whycircussockets`.


Controlling Circus
------------------

Circus provides two command-line tools to manage your running daemon:

- *circusctl*, a management console you can use to perform
  actions such as adding or removing :term:`workers`

- *circus-top*, a top-like console you can use to display the memory and
  cpu usage of your running Circus.

To learn more about these, see :ref:`cli`

Circus also offers a web dashboard that can connect to a
running Circus daemon and let you monitor and interact with it.

To learn more about this feature, see :ref:`circushttpd`


What now ?
==========

If you are a developer and want to leverage Circus in your own project,
write plugins or hooks, go to :ref:`fordevs`.

If you are an ops and want to manage your processes using Circus,
go to :ref:`forops`.


Contributions and Feedback
==========================

More on contributing: :ref:`contribs`.


Useful Links:

- There's a mailing-list for any feedback or question: http://tech.groups.yahoo.com/group/circus-dev/
- The repository and issue tracker are on GitHub : https://github.com/circus-tent/circus
- Join us on the IRC : Freenode, channel **#mozilla-circus**


Documentation index
===================

.. toctree::
   :maxdepth: 2

   installation
   tutorial/index
   for-ops/index
   for-devs/index
   usecases
   design/index
   contributing
   faq
   changelog
   man/index
   glossary
   copyright


