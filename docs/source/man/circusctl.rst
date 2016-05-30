circusctl man page
##################

Synopsis
--------

circusctl [options] command [args]


Description
-----------

circusctl is front end to control the Circus daemon. It is designed to
help the administrator control the functionning of the Circud
**circusd** daemon.


Commands
--------

:add: Add a watcher
:decr: Decrement the number of processes in a watcher
:dstats: Get circusd stats
:get: Get the value of specific watcher options
:globaloptions: Get the arbiter options
:incr: Increment the number of processes in a watcher
:ipython: Create shell into circusd process
:list: Get list of watchers or processes in a watcher
:listen: Subscribe to a watcher event
:listsockets: Get the list of sockets
:numprocesses: Get the number of processes
:numwatchers: Get the number of watchers
:options: Get the value of all options for a watcher
:quit: Quit the arbiter immediately
:reload: Reload the arbiter or a watcher
:reloadconfig: Reload the configuration file
:restart: Restart the arbiter or a watcher
:rm: Remove a watcher
:set: Set a watcher option
:signal: Send a signal
:start: Start the arbiter or a watcher
:stats: Get process infos
:status: Get the status of a watcher or all watchers
:stop: Stop watchers


Options
-------

:--endpoint *ENDPOINT*:
   connection endpoint

:-h, \--help:
   Show the help message and exit

:--json:
   output to JSON

:--prettify:
   prettify output

:--ssh *SSH*:
   SSH Server in the format ``user@host:port``

:--ssh_keyfile *SSH_KEYFILE*:
   path to the keyfile to authorise the user

:--timeout *TIMEOUT*:
   connection timeout

:\--version:
   Displays Circus version and exits.


See Also
--------

`circus` (1), `circusd` (1), `circusd-stats` (1), `circus-plugin` (1), `circus-top` (1).

Full Documentation is available at https://circus.readthedocs.io
