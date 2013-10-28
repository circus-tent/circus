Circus: A Process & Socket Manager
##################################

.. image:: images/circus-medium.png
   :align: right

Circus is a python program which can be used to monitor and control processes and sockets.

Circus can be driven via a command-line interface or programmatically through
its python API. Circus is designed using `ZeroMQ <http://www.zeromq.org/>`_.
See :ref:`design` for more details.

If you are curious about what Circus brings compared to other projects, read :ref:`why`.
If you're coming from Supervisor, read :ref:`supervisor`.


.. warning::

   By default, Circus doesn't secure its messages when sending information
   through ZeroMQ. Before running Circus in a production environment, make sure
   to read the :ref:`Security` page.


To install it and try its features check out the :ref:`examples`.


Running Circus
==============

Circus provides a command-line script call **circusd** that can be used
to manage one or more :term:`watchers`. Each watcher can have one or more
running :term:`processes`.

Circus' command-line tool is configurable using an ini-style
configuration file.

Here's a very minimal example::

    [watcher:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    numprocesses = 5

    [watcher:anotherprogram]
    cmd = another_program
    numprocesses = 2


The file is then passed to *circusd*::

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
==================

Circus provides two command-line tools to manage your running daemon:

- *circusctl*, a management console you can use it to perform
  actions such as adding or removing :term:`workers`

- *circus-top*, a top-like console you can use to display the memory and
  cpu usage of your running Circus.

To learn more about these, see :ref:`cli`


Circus also offers a small web application that can connect to a
running Circus daemon and let you monitor and interact with it.

Running the web application is as simple as adding an **httpd**
option in the ini file in the *circus* section::

    [circus]
    httpd = True


Or if you want, you can run it as a standalone process with::

    $ circushttpd

By default, **circushttpd** runs on the *8080* port.

To learn more about this feature, see :ref:`circushttpd`


Developing with Circus
======================

Circus provides high-level classes and functions that will let you manage
processes in your own applications.

For example, if you want to run four processes forever, you could write:

.. code-block:: python

    from circus import get_arbiter

    myprogram = {"cmd": "python myprogram.py", "numprocesses": 4}

    arbiter = get_arbiter([myprogram])
    try:
        arbiter.start()
    finally:
        arbiter.stop()

This snippet will run four instances of *myprogram* and watch them for you,
restarting them if they die unexpectedly.

To learn more about this, see :ref:`library`


Extending Circus
================

It's easy to extend Circus to create a more complex system, by listening to all
the **circusd** events via its pub/sub channel, and driving it via commands.

That's how the flapping feature works for instance: it listens to all the
processes dying, measures how often it happens, and stops the incriminated
watchers after too many restarts attempts.

Circus comes with a plugin system to help you write such extensions, and
a few built-in plugins you can reuse. See :ref:`plugins`.

You can also have a more subtile startup and shutdown behavior by using the
**hooks** system that will let you run arbitrary code before and after
some processes are started or stopped. See :ref:`hooks`.


More documentation
==================

.. toctree::
   :maxdepth: 2

   installation
   tutorial/index
   for-ops/index
   for-devs/index
   sockets
   usecases
   design/index
   contributing
   faq
   changelog
   glossary
   copyright


Contributions and Feedback
==========================

More on contributing: :ref:`contribs`.


Useful Links:

- There's a mailing-list for any feedback or question: http://tech.groups.yahoo.com/group/circus-dev/
- The repository and issue tracker are on GitHub : https://github.com/mozilla-services/circus
- Join us on the IRC : Freenode, channel **#mozilla-circus**

