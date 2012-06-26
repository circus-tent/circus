Circus Use Cases
================

This chapter presents a few use cases, to give you an idea on how to use
Circus in your environment.


Running a WSGI application
--------------------------


Running a WGSI application with Circus is quite interesting because you can
watch & manage your *web workers* using *circus-top*, *circusctl* or
the Web interface.

Let's take an example with a minimal `Pyramid <http://docs.pylonsproject.org/projects/pyramid/en/latest/>`_
application::


    from pyramid.config import Configurator
    from pyramid.response import Response

    def hello_world(request):
        return Response('Hello %(name)s!' % request.matchdict)

    config = Configurator()
    config.add_route('hello', '/hello/{name}')
    config.add_view(hello_world, route_name='hello')
    application = config.make_wsgi_app()


Save this script into an **app.py** file, then install those projects::

    $ pip install Pyramid
    $ pip install chaussette

Next, make sure you can run your Pyramid application using the **chaussette**
console script::

    $ bin/chaussette app.application
    Application is <pyramid.router.Router object at 0x10a4d4bd0>
    Serving on localhost:8080
    Using <class 'chaussette.backend._waitress.Server'> as a backend

And check that you can reach it by visiting **http://localhost:8080/hello/tarek**

Now that your application is up and running, let's create a Circus
configuration file::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555
    pubsub_endpoint = tcp://127.0.0.1:5556
    stats_endpoint = tcp://127.0.0.1:5557

    [watcher:webworker]
    cmd = chaussette --fd $(circus.socket.webapp) app.application
    use_sockets = True
    numprocesses = 3

    [socket:webapp]
    host = 127.0.0.1
    port = 8080

This file tells Circus to bind a socket on port *8080* and run *chaussette*
workers on that socket -- by passing its fd.

Save it to *server.ini* and try to run it using **circusd** ::

    $ circusd server.ini
    [INFO] Starting master on pid 8971
    [INFO] sockets started
    [INFO] circusd-stats started
    [INFO] webapp started
    [INFO] Arbiter now waiting for commands

Make sure you still get the app on **http://localhost:8080/hello/tarek**.

Congrats ! you have a WSGI application running 3 workers.

You can run the :ref:`circushttpd` or the :ref:`cli`, and enjoy Circus management.



