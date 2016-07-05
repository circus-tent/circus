.. _why:

Why should I use Circus instead of X ?
######################################


1. **Circus simplifies your web stack process management**

   Circus knows how to manage processes *and* sockets, so you don't
   have to delegate web workers management to a WGSI server.

   See :ref:`whycircussockets`


2. **Circus provides pub/sub and poll notifications via ZeroMQ**

  Circus has a :term:`pub/sub` channel you can subscribe to. This channel
  receives all events happening in Circus. For example, you can be
  notified when a process is :term:`flapping`, or build a client that
  triggers a warning when some processes are eating all the CPU or RAM.

  These events are sent via a ZeroMQ channel, which makes it different
  from the stdin stream Supervisord uses:

  - Circus sends events in a fire-and-forget fashion, so there's no
    need to manually loop through *all* listeners and maintain their
    states.
  - Subscribers can be located on a remote host.

  Circus also provides ways to get status updates via one-time polls
  on a req/rep channel. This means you can get your information without
  having to subscribe to a stream. The :ref:`cli` command provided by
  Circus uses this channel.

  See :ref:`examples`.


3. **Circus is (Python) developer friendly**

  While Circus can be driven entirely by a config file and the
  *circusctl* / *circusd* commands, it is easy to reuse all or part of
  the system to build your own custom process watcher in Python.

  Every layer of the system is isolated, so you can reuse independently:

  - the process wrapper (:class:`Process`)
  - the processes manager (:class:`Watcher`)
  - the global manager that runs several processes managers (:class:`Arbiter`)
  - and so on…


4. **Circus scales**

  One of the use cases of Circus is to manage thousands of processes without
  adding overhead -- we're dedicated to focusing on this.

.. _supervisor:

Coming from Supervisor
======================

Supervisor is a very popular solution in the Python world and we're
often asked how Circus compares with it.

If you are coming from `Supervisor <http://supervisord.org>`_, this page
tries to give an overview of how the tools differ.


Similarities overview
---------------------

Supervisor & Circus have the same goals - they both manage processes and
provide a command-line script — respectively **supervisord** and **circusd** —
that reads a configuration file, forks new processes and keep them alive.

Circus & Supervisor both have the ability to bind sockets and
let the processes they manage use them. This "pre-fork" model is used
by many web servers out there, like `Apache <https://httpd.apache.org/>`_ or
`Unicorn <http://unicorn.bogomips.org/>`_. Having this option in a process
manager can simplify a web app stack: all processes and sockets are managed
by a single tool. For Python, `Chaussette <https://chaussette.readthedocs.io/>`_
allows WSGI severs to use the already-opened sockets provided by the socket
managers in both **circusd** and **supervisord**.

Both projects provide a way to control a running daemon via another script.
respectively **supervisorctl** and **circusctl**. They also both have
events and a way to subscribe to them. The main difference is the
underlying technology: Supervisor uses XML-RPC for interacting with
the daemon, while Circus uses ZeroMQ.

Circus & Supervisor both have a web interface to display what's going
on. Circus' is more advanced because you can follow in real time what's
going on and interact with the daemon. It uses web sockets and is developed
in a separate project (`circus-web <https://github.com/circus-tent/circus-web>`_.)

There are many other subtle differences in the core design, we
might list here one day… In the meantime, you can learn more about circus
internals in :ref:`design`.


Configuration
-------------

Both systems use an ini-like file as a configuration.

- `Supervisor documentation <http://supervisord.org/configuration.html>`_
- `Circus documentation <https://circus.readthedocs.io/en/latest/for-ops/configuration/>`_

Here's a small example of running an application with Supervisor. In this
case, the application will be started and restarted in case it crashes ::

    [program:example]
    command=npm start
    directory=/home/www/my-server/
    user=www-data
    redirect_stderr=True

In Circus, the same configuration is done by::

    [watcher:example]
    cmd=npm start
    working_dir=/home/www/my-server/
    user=www-data
    stderr_stream.class=StdoutStream

Notice that the stderr redirection is slightly different in Circus. The
tool does not have a **tail** feature like in Supervisor, but will let
you hook any piece of code to deal with the incoming stream. You
can create your own stream hook (as a Class) and do whatever you want with
the incoming stream. Circus provides some built-in stream classes
like **StdoutStream**, **FileStream**, **WatchedFileStream**, or **TimedRotatingFileStream**.

.. XXX add more complex examples
