Welcome to Circus' documentation!
=================================

Contents:

.. toctree::
   :maxdepth: 2


XXX to reorganize

Circus is a program that runs and watches several processes.

Circus can be driven through a CLI.


Organization and terms
----------------------

- Each program to run is called a *show*
- Each show can run with a certain amount of *flies*
- A *fly* spawns a independant process
- A *trainer* is responsible to run all the *shows* and make sure all the flies
  behave.

::

    Trainer
       |
       |-- show 1
       |    |
       |    |-- fly 1
       |    |-- fly 2
       |
       |-- show 2
            |
            |-- fly 3

Configuration
-------------

Circus is configured with a ini-style file. Example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555

    [show:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    num_flies = 5



Test it
-------

To test it run the following command:

    $ cd examples && circusd circus.ini

It should launch 5 workers.

