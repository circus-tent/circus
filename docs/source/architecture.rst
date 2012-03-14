Architecture
------------

.. image:: images/circus-architecture.png
   :align: center



**Show**
    A *show* is the program you tell Circus to run.  A single Circus
    instance can run one or more shows.
**Flies**
    A *fly* is an independent OS process instance of your program.
    A single show can run one or more flies.
**Trainer**
    The *trainer* is responsible for managing all the shows within circus,
    ensuring all flies run correctly.
**Controller**
    A *controller* contains the set of actions that con be performed on
    the trainer.
**PubSub**
    Circus has a *pubsub* that receives events from the shows and dispatches
    them to all subscribers.
**Flapping detection**
    The *flapping detection* subscribes to events and detects when some
    flies are constantly restarting.
**Remote controller**
    The *remote controller* allows you to communicate with the controller 
    via ZMQ to control Circus.
