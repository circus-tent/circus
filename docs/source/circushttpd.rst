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
   :target: _images/web-login.png
   :align: center
   :height: 400px



The Web Console is ready to be connected to a Circus system, given its **endpoint**.
By default the endpoint is *tcp://127.0.0.1:5557*.

Once you hit *Connect*, the web application will connect to the Circus system.

With the Web Console logged in, you should get a list of watchers, and a real-time
status of the two Circus processes (circusd and circusd-stats).

.. image:: images/web-index.png
   :target: _images/web-index.png
   :align: center
   :height: 400px

You can click on the status of each watcher to toggle it from **Active** (green)
to **Inactive** (red). This change is effective immediatly and let you start & stop
watchers.

If you click on the watcher name, you will get a web page for that particular
watcher, with its processes:

.. image:: images/web-watchers.png
   :target: _images/web-watchers.png
   :align: center
   :height: 400px

On this screen, you can add or remove processes, and kill existing ones.

Last but not least, you can add a brand new watcher by clicking on the *Add Watcher* link
in the left menu:

.. image:: images/web-add-watcher.png
   :target: _images/web-add-watcher.png
   :align: center
   :height: 400px



Running behind Nginx
====================

XXX Talk about security


