.. _plugins:

The Plugin System
=================

Circus comes with a plugin system that will let you interact with **circusd**.

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
- XXX


Writing a plugin
----------------

XXX


Using a plugin
--------------

XXX
