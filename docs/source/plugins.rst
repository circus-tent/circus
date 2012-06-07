.. _plugins:

The Plugin System
=================

Circus comes with a plugin system which let you interact with **circusd**.

.. note::

   We might add circusd-stats support to plugins later on


A Plugin is composed of two parts:

- a ZMQ subscriber to all events published by **circusd**
- a ZMQ client to send commands to **circusd**

A few examples of some plugins you could create with this system:

- a notification system that sends e-mail alerts when a watcher is flapping
- a logger
- a tool that add or remove processes depending on the load
- etc.

Circus itself provides a few plugins:

- a statsd plugin, that sends to statsd all events emited by circusd
- the flapping feature which avoid to re-launch processes infinitely when they
  die too quickly.
- many more to come !


The CircusPlugin class
----------------------

Circus provides a base class to help you implement plugins:
:class:`circus.plugins.CircusPlugin`


.. autoclass:: circus.plugins.CircusPlugin
   :members: call, cast, handle_recv, handle_stop, handle_init

The class is overriding :func:`threading.Thread` so the plugin is executed
in a separate thread than the main event loop.

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
----------------

Let's write a plugin that logs in a file every event happening in
**circusd**. It takes one argument which is the filename.

The plugin could look like this::

    from circus.plugins import CircusPlugin


    class Logger(CircusPlugin):

        name = 'logger'

        def __init__(self, filename, **kwargs):
            super(Logger, self).__init__(**kwargs)

            self.filename = filename
            self.file = None

        def handle_init(self):
            self.file = open(self.filename, 'a+')

        def handle_stop(self):
            self.file.close()

        def handle_recv(self, data):
            topic, msg = data
            self.file.write('%s::%s' % (topic, msg))


That's it ! This class can be saved in any package/module, as long as it can be seen
by Python.

For example, :class:`Logger` could be found in a *plugins* module in a
*myproject* package.


Using a plugin
--------------

Using a plugin in a Circus configuration is done by adding a **[plugin:NAME]**
section in the configuration file, where *NAME* is a unique name for your
plugin::


    [plugin:logger]
    use = myproject.plugins.Logger
    filename = /var/myproject/circus.log


**use** is mandatory and points to the fully qualified name of the plugin.

When Circus starts, it creates one instance of the pointed class, and
pass any other variable contained in the section to the plugin constructor
via the **config** mapping.

You can also programmatically add plugins when you create a
:class:`circus.arbiter.Arbiter` class or use :func:`circus.get_arbiter`,
see :ref:`library`.


Performances
------------

Since every plugin is loaded in its own thread, it should not impact
the overall performances of the system as long as the work done by the
plugin is not CPU-heavy.

If you have a plugin that's doing a lot of work, a better option is
to execute it on its own process by using the *process* flag.

When this flag is activated, Circus starts the plugin as a watcher.

.. warning::

   The process option is not yet implemented.
