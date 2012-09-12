CHANGES
=======

0.6
---

* Patching protocols name for sockets - #248


0.5.2 - 2012-07-26
------------------

* now patching the thread module from the stdlib
  to avoid some Python bugs - #203
* better looking circusctl help screen
* uses pustil get_nice() when available (nice was deprecated) - #208
* added max_age support - #221
* only call listen() on SOCK_STREAM or SOCK_SEQPACKET sockets
* make sure the controller empties the plugins list in update_watchers() - #220
* added --log-level and --log-output to circushttpd
* fix the process killing via the web UI - #219
* now circus is zc.buildout compatible for scripts.
* cleanup the websocket when the client disconnect - #225
* fixed the default value for the endpoint - #199
* splitted circushttpd in logical modules


0.5.1 - 2012-07-11
------------------

* Fixed a bunch of typos in the documentation
* Added the debug option
* Package web-requirements.txt properly
* Added a errno error code in the messages - fixes #111

0.5 - 2012-07-06
----------------

* added socket support
* added a listsocket command
* sockets have stats too !
* fixed a lot of small bugs
* removed the wid - now using pid everywhere
* faster tests
* changed the variables syntax
* use pyzmq's ioloop in more places
* now using iowait for all select() calls
* incr/decr commands now have an nbprocess parameter
* Add a reproduce_env option to watchers
* Add a new UNEXISTING status to the processes
* Added the global *httpd* option to run circushttpd as a watcher


0.4 - 2012-06-12
----------------

* Added a plugin system
* Added a "singleton" option for watchers
* Fixed circus-top screen flickering
* Removed threads from circus.stats in favor of zmq periodic callbacks
* Enhanced the documentation
* Circus client now have a send_message api
* The flapping feature is now a plugin
* Every command line tool have a --version option
* Added a statsd plugin (sends the events from circus to statsd)
* The web UI now uses websockets (via socketio) to get the stats
* The web UI now uses sessions for "flash messages" in the web ui

0.3.4 - 2012-05-30
------------------

- Fixed a race condition that prevented the controller
  to cleanly reap finished processes.
- Now check_flapping can be controlled in the configuration.
  And activated/deactivated per watcher.


0.3.3 - 2012-05-29
------------------

- Fixed the regression on the uid handling

0.3.2 - 2012-05-24
------------------

- allows optional args property to add_watcher command.
- added circushttpd, circus-top and circusd-stats
- allowing Arbiter.add_watcher() to set all Watcher option
- make sure the redirectors are re-created on restarts


0.3.1 - 2012-04-18
------------------

- fix: make sure watcher' defaults aren't overrided
- added a StdoutStream class.

0.3 - 2012-04-18
----------------

- added the streaming feature
- now displaying coverage in the Sphinx doc
- fixed the way the processes are killed (no more SIGQUIT)
- the configuration has been factored out
- setproctitle support


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
