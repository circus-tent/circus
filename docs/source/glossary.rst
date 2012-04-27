.. _glossary:

Glossary
========

.. image:: images/circus-architecture.png
   :align: center

.. glossary::
    :sorted:

    watchers
    watcher
        A *watcher* is the program you tell Circus to run.  A single Circus
        instance can run one or more watchers.

    process
    processes
        A *process* is an independent OS process instance of your program.
        A single watcher can run one or more processes.

    arbiter
        The *arbiter* is responsible for managing all the watchers within
        circus, ensuring all processes run correctly.

    controller
        A *controller* contains the set of actions that con be performed on
        the arbiter.

    pub/sub
        Circus has a *pubsub* that receives events from the watchers and
        dispatches them to all subscribers.

    flapping
        The *flapping detection* subscribes to events and detects when some
        processes are constantly restarting.

    remote controller
        The *remote controller* allows you to communicate with the controller
        via ZMQ to control Circus.
