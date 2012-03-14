.. _library:

Circus Library
--------------


.. autofunction:: circus.get_trainer

Example:

.. code-block:: python

   from circus import get_trainer

   trainer = get_trainer("myprogram", numflies=3)
   try:
       trainer.start()
   finally:
       trainer.stop()

   

