Circus: A Process & Socket Manager
==================================

.. image:: images/circus-medium.png
   :align: right

Circus is a process & socket manager. It can be used to monitor and control
processes and sockets.

Circus can be driven via a command-line interface or programmatically through
its python API.

It shares some of the goals of `Supervisord <http://supervisord.org>`_,
`BluePill <https://github.com/arya/bluepill>`_ and
`Daemontools <http://cr.yp.to/daemontools.html>`_. If you are curious about
what Circus brings compared to other projects, read the :ref:`why`.

.. note::

   Before using Circus on a real system, please make sure to read the
   :ref:`Security` page.

The documentation is split in the following sections:

* Using Circus from the command line :ref:`cli`
* Using Circus as a library :ref:`library`
* Extending Circus via plugins :ref:`plugins`
* Developping for Circus (Internals) :ref:`design`

You can also go trough all the sections of the documentation that are listed
here:

.. toctree::
   :maxdepth: 2

   installation
   configuration
   cli
   commands
   circushttpd
   sockets
   library
   plugins
   deployment
   security
   design
   rationale
   examples
   usecases
   coverage
   glossary
   contributing
   adding_new_commands
   copyright


Contributions and Feedback
--------------------------

If you want to contribute to Circus, go and read :ref:`contribs`.

Useful Links:

- There's a maling list for any feedback or question: http://tech.groups.yahoo.com/group/circus-dev/
- The repository and issue tracker is at GitHub : https://github.com/mozilla-services/circus
- Join us on the IRC : Freenode, channel **#mozilla-circus**.
