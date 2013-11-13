.. _develop_plugins:

Writing plugins
###############

Circus comes with a plugin system which lets you interact with **circusd**.

.. note::

   We might add circusd-stats support to plugins later on.


A Plugin is composed of two parts:

- a ZMQ subscriber to all events published by **circusd**
- a ZMQ client to send commands to **circusd**

Each plugin is run as a separate process under a custom watcher.

A few examples of some plugins you could create with this system:

- a notification system that sends e-mail alerts when a watcher is flapping
- a logger
- a tool that adds or removes processes depending on the load
- etc.

Circus itself comes with a few :ref:`built-in plugins <plugins>`.


The CircusPlugin class
======================

Circus provides a base class to help you implement plugins:
:class:`circus.plugins.CircusPlugin`


.. autoclass:: circus.plugins.CircusPlugin
   :members: call, cast, handle_recv, handle_stop, handle_init

When initialized by Circus, this class creates its own event loop that receives
all **circusd** events and pass them to :func:`handle_recv`. The data received
is a tuple containing the topic and the data itself.

:func:`handle_recv` **must** be implemented by the plugin.

The :func:`call` and :func:`cast` methods can be used to interact with
**circusd** if you are building a Plugin that actively interacts with
the daemon.

:func:`handle_init` and :func:`handle_stop` are just convenience methods
you can use to initialize and clean up your code. :func:`handle_init` is
called within the thread that just started. :func:`handle_stop` is called
in the main thread just before the thread is stopped and joined.


Writing a plugin
================

Let's write a plugin that logs in a file every event happening in
**circusd**. It takes one argument which is the filename.

The plugin may look like this::

    from circus.plugins import CircusPlugin


    class Logger(CircusPlugin):

        name = 'logger'

        def __init__(self, *args, **config):
            super(Logger, self).__init__(*args, **config)
            self.filename = config.get('filename')
            self.file = None

        def handle_init(self):
            self.file = open(self.filename, 'a+', buffering=1)

        def handle_stop(self):
            self.file.close()

        def handle_recv(self, data):
            watcher_name, action, msg = self.split_data(data)
            msg_dict = self.load_message(msg)
            self.file.write('%s %s::%r\n' % (action, watcher_name, msg_dict))


That's it ! This class can be saved in any package/module, as long as it can be seen
by Python.

For example, :class:`Logger` may be found in a *plugins* module within a
*myproject* package.

Async requests
--------------

In case you want to make any asynchronous operations (like a Tornado call or using
periodicCall) make sure you are using the right loop. The loop you always want to 
be using is self.loop as it gets set up by the base class. The default loop often
isn't the same and therefore code might not get executed as expected.


Trying a plugin
===============

You can run a plugin through the command line with the **circus-plugin** command,
by specifying the plugin fully qualified name::

    $ circus-plugin --endpoint tcp://127.0.0.1:5555 --pubsub tcp://127.0.0.1:5556 --config filename:circus-events.log myproject.plugins.Logger
    [INFO] Loading the plugin...
    [INFO] Endpoint: 'tcp://127.0.0.1:5555'
    [INFO] Pub/sub: 'tcp://127.0.0.1:5556'
    [INFO] Starting

Another way to run a plugin is to let Circus handle its initialization. This is done
by adding a **[plugin:NAME]** section in the configuration file, where *NAME* is a unique
name for your plugin:

.. code-block:: ini

    [plugin:logger]
    use = myproject.plugins.Logger
    filename = /var/myproject/circus.log

**use** is mandatory and points to the fully qualified name of the plugin.

When Circus starts, it creates a watcher with one process that runs the pointed class,
and pass any other variable contained in the section to the plugin constructor
via the **config** mapping.

You can also programmatically add plugins when you create a
:class:`circus.arbiter.Arbiter` class or use :func:`circus.get_arbiter`,
see :ref:`library`.


Performances
============

Since every plugin is loaded in its own process, it should not impact
the overall performances of the system as long as the work done by the
plugin is not doing too many calls to the **circusd** process.
