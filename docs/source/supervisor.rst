.. _supervisor:

Coming from Supervisor
======================

If you are coming from `Supervisor <http://supervisord.org_>`_, this page
tries to give an overview of how the tools differ.


Differences overview
--------------------

Supervisor & Circus have the same goals - they both manage processes and
provide a command-line script — respectively **supervisord** and **circusd**—
that reads a configuration file, forks new processes and maintain them alive.

Circus has an extra feature: the ability to bind sockets and
let the processes it manages use them. This "pre-fork" model is used
by many web servers out there, like `Apache <https://httpd.apache.org/>`_ or 
`Unicorn <http://unicorn.bogomips.org/>`_. Having this option in Circus 
can simplify a web app stack: all processes and sockets are managed by 
a single tool.

Both projects provide a way to control a running daemon via another script.
respectively **supervisorctl** and **circusctl**. They also both have
events and a way to subscribe to them. The main difference is the
underlying technology: Supervisor uses XML-RPC for interacting with
the daemon, while Circus uses ZeroMQ.

Circus & Supervisor both have a web interface to display what's going
on. Circus' one is more advanced because you can follow in real time
what's going on and interact with the daemon. It uses web sockets and
is developed in a separate project (`circus-web <https://github.com/mozilla-services/circus-web>`_.)

There are many other subtle differences in the core design, we
might list here one day… In the meantime, you can learn more about circus 
internals in :ref:`design`.


Configuration
-------------

Both systems use an ini-like file as a configuration.

- `Supervisor documentation <http://supervisord.org/configuration.html>`_
- `Circus documentation <http://circus.readthedocs.org/en/latest/configuration/>`_

Here's a small example of running an application with Supervisor. In this
case, the application will be started and restarted in case it crashes ::

    [program:example]
    command=/usr/local/bin/uwsgi --ini /etc/uwsgi.ini


In Circus, the same configuration is done by::

    [watcher:example]
    cmd=/usr/local/bin/uwsgi --ini /etc/uwsgi.ini


XXX add more complex examples

