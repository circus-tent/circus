.. _sockets:

Circus Sockets
==============

Circus can bind network sockets and manage them as it does for processes.

The main idea is that a child process that's created by Circus to run one of
the watcher's command can inherit from all the opened file descriptors.

That's how Apache or Unicorn works, and many other tools out there.

Goal
----

The goal of having sockets managed by Circus is to be able to manage network
applications in Circus exactly like other applications.

For example, if you use Circus with `Chaussette <http://chaussette.rtfd.org>`_
-- a WGSI server, you can get a very fast web server running and manage
*"Web Workers"* in Circus as you would do for any other process.

Splitting the socket managment from the network application itself offers
a lot of opportunities to scale and manage your stack.


Design
------

The gist of the feature is done by binding the socket and start listening
to it in **circusd**:

.. code-block:: python

    import socket

    sock = socket.socket(FAMILY, TYPE)
    sock.bind((HOST, PORT))
    sock.listen(BACKLOG)
    fd = sock.fileno()


Circus then keeps track of all the opened fds, and let the processes it
runs as children have access to them if they want.

If you create a small Python network script that you intend to run in Circus,
it could look like this:

.. code-block:: python

    import socket
    import sys

    fd = int(sys.argv[1])   # getting the FD from circus
    sock = socket.fromfd(fd, FAMILY, TYPE)

    # dealing with one request at a time
    while True:
        conn, addr = sock.accept()
        request = conn.recv(1024)
        .. do something ..
        conn.sendall(response)
        conn.close()


Then Circus could run like this:

.. code-block:: ini

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555
    pubsub_endpoint = tcp://127.0.0.1:5556
    stats_endpoint = tcp://127.0.0.1:5557

    [watcher:dummy]
    cmd = mycoolscript $(circus.sockets.foo)
    use_sockets = True
    warmup_delay = 0
    numprocesses = 5

    [socket:foo]
    host = 127.0.0.1
    port = 8888

*$(circus.sockets.foo)* will be replaced by the FD value once the socket is
created and bound on the 8888 *port*.


Real-world example
------------------

`Chaussette <http://chaussette.rtfd.org>`_ is the perfect Circus companion if
you want to run your WSGI application.

Once it's installed, running 5 **meinheld** workers can be done by creating a
socket and calling the **chaussette** command in a worker, like this:

.. code-block:: ini

    [circus]
    endpoint = tcp://127.0.0.1:5555
    pubsub_endpoint = tcp://127.0.0.1:5556
    stats_endpoint = tcp://127.0.0.1:5557

    [watcher:web]
    cmd = chaussette --fd $(circus.sockets.web) --backend meinheld mycool.app
    use_sockets = True
    numprocesses = 5

    [socket:web]
    host = 0.0.0.0
    port = 8000


We did not publish benchmarks yet, but a Web cluster managed by Circus with a Gevent
or Meinheld backend is as fast as any pre-fork WSGI server out there.


.. _whycircussockets:


Circus stack v.s. Classical stack
---------------------------------

In a classical WSGI stack, you have a server like Gunicorn that serves on a port
or an unix socket and is usually deployed behind a web server like Nginx:

.. image:: images/classical-stack.png


Clients call Nginx, which reverse proxies all the calls to Gunicorn.

If you want to make sure the Gunicorn process stays up and running, you have to use
a program like Supervisord or upstart.

Gunicorn in turn watches for its processes ("workers").

In other words you are using two levels of process managment. One that you manage
and control (supervisord), and a second one that you have to manage in a different UI,
with a different philosophy and less control over what's going on (the wsgi server's one)

This is true for Gunicorn and most multi-processes WSGI servers out there
I know about. uWsgi is a bit different as it offers plethoras of options.

But if you want to add a Redis server in your stack, you *will* end up with
managing your stack processes in two different places.


Circus' approach on this is to manage processes *and* sockets.

A Circus stack can look like this:

.. image:: images/circus-stack.png


So, like Gunicorn,
Circus is able to bind a socket that will be proxied by Nginx. Circus don't
deal with the requests but simply binds the socket. It's then up to a web worker
process to accept connections on the socket and do the work.

It provides equivalent features than Supervisord but will also let you
manage all processes at the same level, wether they are web workers or Redis or
whatever. Adding a new web worker is done exactly like adding a new Redis
process.

Benches
=======

We did a few benches to compare Circus & Chaussette with Gunicorn. To
summarize, Circus is not adding any overhead and you can pick up many
different backends for your web workers.

See:

- http://blog.ziade.org/2012/06/28/wgsi-web-servers-bench
- http://blog.ziade.org/2012/07/03/wsgi-web-servers-bench-part-2



