CHANGES
=======

0.3 - 2012-????
---------------

- ?

0.2 - 2012-04-04
----------------

- Removed the *show* name. replaced by *watcher*.
- Added support for setting process **rlimit**.
- Added support for include dirs in the config file.
- Fixed a couple of leaking file descriptors.
- Fixed a core dump in the flapping
- Doc improvments
- Make sure circusd errors properly when another circusd
  is running on the same socket.
- get_arbiter now accepts several watchers.
- Fixed the cmd vs args vs executable in the process init.
- Fixed --start on circusctl add


0.1 - 2012-03-20
----------------

- initial release
