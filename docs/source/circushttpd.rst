.. _circushttpd:

The Web Console
===============

Circus comes with a Web Console that can be used to manage the system.

The Web Console will let you:

* Connect to any running Circus system
* Watch the processes CPU and Memory usage in real-time
* Add or kill processes
* Add a new watcher


.. note::

   The real-time CPU & Memory usage feature uses the stats socket.
   If you want to activate it, make sure the Circus system you'll
   connect to has the stats enpoint enabled in its configuration::

     [circus]
     ...
     stats_endpoint = tcp://127.0.0.1:5557
     ...

   By default, this option is not activated.


To enable the console, run the **circushttpd** script::


    $ bin/circushttpd
    Bottle server starting up (using WSGIRefServer())...
    Listening on http://localhost:8080/
    Hit Ctrl-C to quit.


By default the script will run the Web Console on port 8080, but the --port option can
be used to change it.

Using the console
=================

Once the script is running, you can open a browser and visit *http://localhost:8080*.
You should get this screen:

.. image:: images/web-login.png
   :target: ../_images/web-login.png
   :align: center
   :height: 400px



The Web Console is ready to be connected to a Circus system, given its **endpoint**.
By default the endpoint is *tcp://127.0.0.1:5557*.

Once you hit *Connect*, the web application will connect to the Circus system.

With the Web Console logged in, you should get a list of watchers, and a real-time
status of the two Circus processes (circusd and circusd-stats).

.. image:: images/web-index.png
   :target: ../_images/web-index.png
   :align: center
   :height: 400px

You can click on the status of each watcher to toggle it from **Active** (green)
to **Inactive** (red). This change is effective immediatly and let you start & stop
watchers.

If you click on the watcher name, you will get a web page for that particular
watcher, with its processes:

.. image:: images/web-watchers.png
   :target: ../_images/web-watchers.png
   :align: center
   :height: 400px

On this screen, you can add or remove processes, and kill existing ones.

Last but not least, you can add a brand new watcher by clicking on the *Add Watcher* link
in the left menu:

.. image:: images/web-add-watcher.png
   :target: ../_images/web-add-watcher.png
   :align: center
   :height: 400px



Running behind Nginx & Gunicorn
===============================

*circushttpd* is a WSGI application so you can run it with any web server that's
compatible with that protocol. By default it uses the standard library
**wsgiref** server, but that server does not really support any load.

A nice combo is Gunicorn & Nginx:

- Gunicorn is the WSGI web server and serves the Web application on the
  8080 port.
- Nginx acts as a proxy in front of Gunicorn. It an also deal with security.

Gunicorn
--------

To run Gunicorn, make sure Gunicorn is installed in your environment and
simply use the **--server** option::

    $ pip install gunicorn
    $ bin/circushttpd --server gunicorn
    Bottle server starting up (using GunicornServer())...
    Listening on http://localhost:8080/
    Hit Ctrl-C to quit.

    2012-05-14 15:10:54 [13536] [INFO] Starting gunicorn 0.14.2
    2012-05-14 15:10:54 [13536] [INFO] Listening at: http://127.0.0.1:8080 (13536)
    2012-05-14 15:10:54 [13536] [INFO] Using worker: sync
    2012-05-14 15:10:54 [13537] [INFO] Booting worker with pid: 13537


If you want to use another server, you can pick any server listed in
http://bottlepy.org/docs/dev/tutorial.html#multi-threaded-server

Nginx
-----

To hook Nginx, you define a *location* directive that proxies the calls
to Gunicorn.

Example::

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_pass http://127.0.0.1:8080;
    }

If you want a more complete Nginx configuration example, have a
look at : http://gunicorn.org/deploy.html


Password-protect circushttpd
----------------------------

As explained in the :ref:`Security` page, running *circushttpd* is pretty
unsafe. We don't provide any security in Circus itself, but you can protect
your console at the NGinx level, by using http://wiki.nginx.org/HttpAuthBasicModule

Example::

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_pass http://127.0.0.1:8080;
        auth_basic            "Restricted";
        auth_basic_user_file  /path/to/htpasswd;
    }


The **htpasswd** file contains users and their passwords, and a password
prompt will pop when you access the console.

You can use Apache's htpasswd script to edit it, or the Python script they
provide at: http://trac.edgewall.org/browser/trunk/contrib/htpasswd.py

Of course that's just one way to protect your web console, you could use
many other techniques.
