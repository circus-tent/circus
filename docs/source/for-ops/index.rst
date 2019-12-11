.. _forops:

Circus for Ops
##############

.. warning::

   By default, Circus doesn't secure its messages when sending information
   through ZeroMQ. Before running Circus in a production environment, make sure
   to read the :ref:`Security` page.

The first step to manage a Circus daemon is to write its configuration file.
See :ref:`configuration`. If you are deploying a web stack, have a look at
:ref:`sockets`.

Circus can be deployed using Python 2.7, 3.2 or 3.3 - most deployments
out there are done in 2.7. To learn how to deploy Circus, check out
:ref:`deployment`.

To manage a Circus daemon, you should get familiar with the list of
:ref:`commands` you can use in **circusctl**. Notice that you can have the same
help online when you run **circusctl** as a shell.

We also provide **circus-top**, see :ref:`cli`, and a nice web dashboard, see
:ref:`circushttpd`.

For quick watcher and process management – start, stop, increment, decrement
etc – there is a Tcl/Tk interface. See `Ringmaster <https://github.com/viotti/ringmaster>`_.

Last, to get the most out of Circus, make sure to check out how
to use plugins and hooks. See :ref:`plugins` and :ref:`hooks`.


Ops documentation index
-----------------------

.. toctree::
   :maxdepth: 1

   configuration
   commands
   cli
   circusweb
   sockets
   using-plugins
   deployment
   papa

