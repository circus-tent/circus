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
**Client**
    The *client* allows you to communicate with the controller via ZMQ to
    control Circus.
