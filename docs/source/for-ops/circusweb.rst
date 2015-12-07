.. _circushttpd:

The Web Console
###############

Circus comes with a Web Console that can be used to manage the system.

The Web Console lets you:

* Connect to any running Circus system
* Watch the processes CPU and Memory usage in real-time
* Add or kill processes
* Add new watchers

.. note::

   The real-time CPU & Memory usage feature uses the stats socket.
   If you want to activate it, make sure the Circus system you'll
   connect to has the stats enpoint enabled in its configuration::

     [circus]
     statsd = True

   By default, this option is not activated.

The web console is its own package, you need to install::

    $ pip install circus-web

To enable the console, add a few options in the Circus ini file::

    [circus]
    httpd = True
    httpd_host = localhost
    httpd_port = 8080


*httpd_host* and *httpd_port* are optional, and default to *localhost* and *8080*.

If you want to run the web app on its own, just run the **circushttpd** script::

    $ circushttpd
    Bottle server starting up...
    Listening on http://localhost:8080/
    Hit Ctrl-C to quit.

By default the script will run the Web Console on port 8080, but the --port option can
be used to change it.

Using the console
=================

Once the script is running, you can open a browser and visit *http://localhost:8080*.
You should get this screen:

.. image:: web-login.png
   :align: center
   :height: 400px


The Web Console is ready to be connected to a Circus system, given its **endpoint**.
By default the endpoint is *tcp://127.0.0.1:5555*.

Once you hit *Connect*, the web application will connect to the Circus system.

With the Web Console logged in, you should get a list of watchers, and a real-time
status of the two Circus processes (circusd and circusd-stats).

.. image:: web-index.png
   :align: center
   :height: 400px

You can click on the status of each watcher to toggle it from **Active** (green)
to **Inactive** (red). This change is effective immediatly and let you start & stop
watchers.

If you click on the watcher name, you will get a web page for that particular
watcher, with its processes:

.. image:: web-watchers.png
   :align: center
   :height: 400px

On this screen, you can add or remove processes, and kill existing ones.

Last but not least, you can add a brand new watcher by clicking on the *Add Watcher* link
in the left menu:

.. image:: web-add-watcher.png
   :align: center
   :height: 400px


Running behind Nginx
====================

Nginx can act as a proxy and security layer in front of circus-web.

.. note:: To receive real-time status updates and graphs in circus-web, you must provide a Nginx proxy solution that has websocket support

Nginx >= 1.3.13
---------------

As of Nginx>=1.3.13 websocket support is built-in, so there is no need to combine Nginx with Varnish or HAProxy. 
An example Nginx config with websocket support:


.. code-block:: ini

    upstream circusweb_server {
      server 127.0.0.1:8080;
    }

    server {
     listen   80;
     server_name  _;

     location / {
       proxy_pass http://circusweb_server;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto http;
       proxy_redirect off;
      }

     location ~/media/\*(.png|.jpg|.css|.js|.ico)$ {
       alias /path_to_site-packages/circusweb/media/;
      }
    }


Nginx < 1.3.13
--------------

Nginx versions < 1.3.13 do not have websocket support built-in.

To provide websocket support for circus-web when using Nginx < 1.3.13, you can combine Nginx with Varnish or HAProxy. That is, Nginx in front of circus-web, with Varnish or HAProxy in front of Nginx.

The example below shows the combined Nginix and Varnish configuration required to proxy circus-web and provide websocket support.

**Nginx configuration:**

.. code-block:: ini

    upstream circusweb_server {
      server 127.0.0.1:8080;
    }

    server {
     listen   8001;
     server_name  _;

     location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_pass http://circusweb_server;
      }

     location ~/media/\*(.png|.jpg|.css|.js|.ico)$ {
       alias /path_to_site-packages/circusweb/media/;
      }
    }

If you want more Nginx configuration options, see http://wiki.nginx.org/HttpProxyModule.

**Varnish configuration:**


.. code-block:: ini


    backend default {
        .host = "127.0.0.1";
        .port = "8001";
    }

    backend socket {
        .host = "127.0.0.1";
        .port = "8080";
        .connect_timeout = 1s;
        .first_byte_timeout = 2s;
        .between_bytes_timeout = 60s;
    }

    sub vcl_pipe {
         if (req.http.upgrade) {
             set bereq.http.upgrade = req.http.upgrade;
         }
    }

    sub vcl_recv {
        if (req.http.Upgrade ~ "(?i)websocket") {
            set req.backend = socket;
          return (pipe);
        }
    }

In the Varnish configuration example above two backends are defined.
One serving the web console and one serving the socket connections.
Web console requests are bound to port 8001. The Nginx 'server' directive should be configured to listen on port 8001.

Websocket connections are upgraded and piped directly to the circushttpd process listening on port 8080 by Varnish. i.e. bypassing the Nginx proxy.

Ubuntu
------

Since the version 13.10 (*Saucy*), Ubuntu includes Nginx with websocket support in its own repositories. For older versions, 
you can install Nginx>=1.3.13 from the official Nginx stable PPA, as so:

.. code-block:: sh

    sudo apt-get install python-software-properties
    sudo add-apt-repository ppa:nginx/stable
    sudo apt-get update
    sudo apt-get install nginx
    nginx -v



Password-protect circushttpd
============================

As explained in the :ref:`Security` page, running *circushttpd* is pretty
unsafe. We don't provide any security in Circus itself, but you can protect
your console at the NGinx level, by using http://wiki.nginx.org/HttpAuthBasicModule

Example::

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Host: $http_host;
        proxy_set_header X-Forwarded-Proto: $scheme;
        proxy_redirect off;
        proxy_pass http://127.0.0.1:8080;
        auth_basic            "Restricted";
        auth_basic_user_file  /path/to/htpasswd;
    }

The **htpasswd** file contains users and their passwords, and a password
prompt will pop when you access the console.

You can use Apache's htpasswd script to edit it, or the Python script they
provide at: http://trac.edgewall.org/browser/trunk/contrib/htpasswd.py

However, there's no native support for the combined use of HTTP Authentication and
WebSockets (the server will throw HTTP 401 error codes). A workaround is to
disable such authentication for the socket.io server.

Example (needs to be added before the previous rule)::

    location /socket.io {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Host: $http_host;
        proxy_set_header X-Forwarded-Proto: $scheme;
        proxy_redirect off;
        proxy_pass http://127.0.0.1:8080;
    }

Of course that's just one way to protect your web console, you could use
many other techniques.

Extending the web console
=========================

We picked *bottle* to build the webconsole, mainly because it's a really
tiny framework that doesn't do much. By having a look at the code of the web
console, you'll eventually find out that it's really simple to understand.

Here is how it's split:

* The `circushttpd.py` file contains the "views" definitions and some code to
  handle the socket connection (via socketio).
* the `controller.py` contains a single class which is in charge of doing the
  communication with the circus controller. It allows to have a nicer high
  level API when defining the web server.

If you want to add a feature in the web console you can reuse the code that's
existing. A few tools are at your disposal to ease the process:

* There is a `render_template` function, which takes the named arguments you
  pass to it and pass them to the template renderer and return the resulting
  HTML. It also passes some additional variables, such as the session, the
  circus version and the client if defined.
* If you want to run commands and doa redirection depending the result of it,
  you can use the `run_command` function, which takes a callable as a first
  argument, a message in case of success and a redirection url.

The :class:`StatsNamespace` class is responsible for managing
the websocket communication on the server side. Its documentation should help
you to understand what it does.


