Circus: A Process & Socket Manager
==================================

.. image:: images/circus-medium.png
   :align: right

Circus is a process & socket manager. It can be used to monitor and control
processes and sockets.

Circus can be driven via a command-line interface or programmatically through
its python API.

It shares some of the goals of `Supervisord <http://supervisord.org>`_,
`BluePill <https://github.com/arya/bluepill>`_ and
`Daemontools <http://cr.yp.to/daemontools.html>`_. If you are curious about
what Circus brings compared to other projects, read :ref:`why`.

Circus is designed using `ZeroMQ <http://www.zeromq.org/>`_. See :ref:`design` for more details.

.. note::

   Circus doesn't secure its messages when sending information through
   ZeroMQ. Before running Circus, make sure you read the :ref:`Security` page.

To install it, check out :ref:`installation`


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

To learn more about these, see :ref:`cli`


Circus also offers a small web application that can connect to a
running Circus daemon and let you monitor and interact with it.

Running the web application is as simple as adding an **httpd**
option in the ini file::

    [circus]
    httpd = True


Or if you want, you can run it as a standalone process with::

    $ circushttpd

By default, **circushttpd** runs on the *8080* port.

To learn more about this feature, see :ref:`circushttpd`


Developing with Circus
----------------------

Circus provides high-level classes and functions that will let you manage
processes in your own applications.

For example, if you want to run four processes forever, you could write:

.. code-block:: python

    from circus import get_arbiter

    arbiter = get_arbiter("myprogram", 4)
    try:
        arbiter.start()
    finally:
        arbiter.stop()

This snippet will run four instances of *myprogram* and watch them for you,
restarting them if they die unexpectedly.

To learn more about this, see :ref:`library`


Extending Circus
----------------

It's easy to extend Circus to create a more complex system, by listening to all
the **circusd** events via its pub/sub channel, and driving it via commands.

That's how the flapping feature works for instance: it listens to all the
processes dying, measures how often it happens, and stops the incriminated
watchers after too many restarts attempts.

Circus comes with a plugin system to help you write such extensions, and
a few built-in plugins you can reuse.

See :ref:`plugins`.


More documentation
------------------

.. toctree::
   :maxdepth: 2

   installation
   configuration
   cli
   commands
   circushttpd
   sockets
   library
   plugins
   deployment
   security
   design
   rationale
   examples
   usecases
   coverage
   glossary
   contributing
   adding_new_commands
   copyright


Contributions and Feedback
--------------------------

More on contribution: :ref:`contribs`.


Useful Links:

- There's a maling list for any feedback or question: http://tech.groups.yahoo.com/group/circus-dev/
- The repository and issue tracker is at GitHub : https://github.com/mozilla-services/circus
- Join us on the IRC : Freenode, channel **#mozilla-circus**

