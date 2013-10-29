.. _glossary:

Glossary: Circus-specific terms
###############################

.. glossary::
    :sorted:

    watcher
    watchers
        A *watcher* is the program you tell Circus to run.  A single Circus
        instance can run one or more watchers.

    worker
    workers
    process
    processes
        A *process* is an independent OS process instance of your program.
        A single watcher can run one or more processes. We also call them
        workers.

    arbiter
        The *arbiter* is responsible for managing all the watchers within
        circus, ensuring all processes run correctly.

    controller
        A *controller* contains the set of actions that can be performed on
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
