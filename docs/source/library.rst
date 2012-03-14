.. _library:

Circus Library
--------------

The Circus package is composed of a high-level :func:`get_trainer`
function and many classes. In most cases, using the high-level function
should be enough, as it creates everything that is needed for Circus to
run.

You can subclass Circus's classes if you need more granular
configurability.


.. autofunction:: circus.get_trainer

Example:

.. code-block:: python

   from circus import get_trainer

   trainer = get_trainer("myprogram", numflies=3)
   try:
       trainer.start()
   finally:
       trainer.stop()



.. autoclass:: circus.show.Show
   :members: send_msg, reap_flies, manage_flies, reap_and_manage_flies,
             spawn_flies, spawn_fly, kill_fly,kill_flies, send_signal_child, stop,start,
             restart, reload, do_action, get_opt


.. autoclass:: circus.trainer.Trainer
   :members: start, stop, reload, numflies, num_shows, get_show, add_show, del_show

