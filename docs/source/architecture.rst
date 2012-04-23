Architecture
------------

.. image:: images/circus-architecture.png
   :align: center



**Watcher**
    A *watcher* is the program you tell Circus to run.  A single Circus
    instance can run one or more watchers.
**Processes**
    A *process* is an independent OS process instance of your program.
    A single watcher can run one or more processes.
**Arbiter**
    The *arbiter* is responsible for managing all the watchers within circus,
    ensuring all processes run correctly.
**Controller**
    A *controller* contains the set of actions that con be performed on
    the arbiter.
**PubSub**
    Circus has a *pubsub* that receives events from the watchers and dispatches
    them to all subscribers.
**Flapping detection**
    The *flapping detection* subscribes to events and detects when some
    processes are constantly restarting.
**Remote controller**
    The *remote controller* allows you to communicate with the controller 
    via ZMQ to control Circus.
