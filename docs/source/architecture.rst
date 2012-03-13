Architecture
------------

.. image:: images/circus-architecture.png
   :align: center



- Each program to run is called a **Show**
- Each show can run with a certain amount of **Flies**
- A **Fly** spawns a independant process
- A **Trainer** is responsible to run all the **Shows** and make sure all the 
  flies behave corectly
- A **Controller** is a set of actions to perform on the trainer.
- The **Client** communicates via ZMQ with the **Controller** to interact
  with the system.


