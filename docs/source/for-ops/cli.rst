.. _cli:

CLI tools
#########

circus-top
==========

*circus-top* is a top-like console you can run to watch
live your running Circus system. It will display the CPU, Memory
usage and socket hits if you have some.


Example of output::

    -----------------------------------------------------------------------
    circusd-stats
     PID                 CPU (%)             MEMORY (%)
    14252                 0.8                 0.4
                          0.8 (avg)           0.4 (sum)

    dummy
     PID                 CPU (%)             MEMORY (%)
    14257                 78.6                0.1
    14256                 76.6                0.1
    14258                 74.3                0.1
    14260                 71.4                0.1
    14259                 70.7                0.1
                          74.32 (avg)         0.5 (sum)

    ----------------------------------------------------------------------



*circus-top* is a read-only console. If you want to interact with the system, use
*circusctl*.


circusctl
=========

*circusctl* can be used to run any command listed in :ref:`commands` . For
example, you can get a list of all the watchers, you can do ::

    $ circusctl list

Besides supporting a handful of options you can also specify the endpoint
*circusctl* should use using the ``CIRCUSCTL_ENDPOINT`` environment variable.
