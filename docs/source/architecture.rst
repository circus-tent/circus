Architecture
------------

.. image:: images/circus-architecture.png
   :align: center



**Show**
    A show is the program you tell to circus to run.  A single circus instance an run one or more shows.
**Flies**
    A fly is an independent OS process instance of your program. A single show can run one or more flies.
**Trainer** 
    The trainer is responsible for managing all the **Shows** within circus and ensures all the flies run correctly.
**Controller** 
    A controller contains the set of actions that con be perform on the trainer.
**Client**
    The client allows you to communicate with the **Controller** via ZMQ to control circus.

