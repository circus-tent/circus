Changelog history
=================

unreleased
----------

- Drop support for tornado<5 and start using asyncio eventl loop - #1129
- Fix mem_info readings to be more reliable - #1128
- Drop support for Python 2.7 & 3.4 - #1126
- Speedup reloadconfig for large number of sockets - #1121
- Do not allow adding watchers with the same lowercase names - #1117
- Do not delete pid file during restart - #1116
- Fix graceful_timeout watcher config option type - #1115

0.16.1 2019-12-27
-----------------
Fix packaging issue.

0.16.0 2019-12-27
-----------------
This release remove support for Python 2.6 & 3.3, and add official support
for Python 3.6, 3.7 & 3.8. It also adds support for PyZMQ 17+.

- Remove support for Python 2.6 & 3.3 - #1110
- Fix compatibility with PyZMQ 17+ - #1111
- Fix compatibility for Python 3.6, 3.7 & 3.8 - #1079, #1085, #1113
- Send add/remove events to plugins - #1086
- Allow 'use_papa' to be called programmatically - #1083
- Allow integer to be used for stop_signal in ini file - #1089
- Add 'on_demand' option to watchers - #1089
- Add before_reap and after_reap hooks - #1104

0.15.0 2018-06-15
-----------------
This release fixes several bugs and explicitely mark Circus as incompatible
with Tornado 5 & PyZMQ 17.

- Born Tornado version to < 5 & PyZMQ version to < 17 - #1030, #1064, #1055
- Fix 'papa_enpoint' config option - #1066
- Circusctl returns non-zero exit code when command fails - #1001
- Fix potential process leaking - #998
- Fix behavior when increasing numprocesses - #997
- Fix Watcher.reap_process - #1036
- Coerce 'max_retry' value to int - #1008
- Drop iowait from the requirements - #1003
- Doc updates - #1022, #1013

0.14.0 2016-08-12
-----------------
This release fixes several bugs and add new options to
Circus sockets and watchers.

- Add stdin_socket option to the watcher - #975
- Add a blocking option to Circus sockets - #973
- Ignore errors when parsing the Pidfile - #866, #969
- Fixes for papa sockets - #930, #968
- Remove I/O operations on closed files - #979, #980
- Accept empty ini sections - #970
- Send SIGKILL to children recursively - #986
- Improve tests stability - #984
- Doc updates - #982, #983, 985

0.13 - 2016-01-27
----------
This release brings Python 3.5 support, a better handling
of stdin for the watchers, a new kill command, and several
interesting bugfixes.

- Compatibility with Python 3.5 - #939, #956
- Add close_child_stdin option to the watchers - #910
- Add 'kill' command - #957
- Fix issues with case for start, stop and restart commands - #927
- Fix AccessDenied error - #920
- DecrProcess was renamed DecrProc - #932
- Fix issues with DecrProc and singleton watchers - #932
- Fix encoding issue with statsd sockets - #947
- Some fixes for Papa sockets - #953, #922
- Minor doc updates

0.12.1 - 2015-08-05
----------
- Fix error when restarting a watcher with an output stream - #913
- Minor doc tweaks


0.12 - 2015-06-02
----------
This release brings Python 3.4, Tornado 4 and Windows support, among
several exciting features and fixes.

The Windows support is still experimental, and does not handle streams.

Major changes:

- Compatibility with Python 3.4 - #768
- Experimental Windows support - #788
- Compatibility with Tornado 4 - #872
- Revamped Debian packaging - #896 - #903
- Add support for Papa process kernel - #850
- Add globing and regex matching for starting, stopping and restarting
  watchers - #829 - #902

More changes:

- Optimization of the shutdown - #784 - #842
- Add possibility to specify virtualenv version for the watchers - #805
- Add --nostop option to the rmwatcher command - #777
- Add a callback to Arbiter.start - #840
- Fix reloading watchers with uppercase letters - #823
- Remove leaking socket in stats daemon - #843
- Fix multicast on SunOS - #876
- Close output streams when stopping a watcher - #885
- Fix signal sending to grandchildren with --recursive - #888


0.11.1 - 2014-05-22
-------------------

- Fixed a regression that broke Circus on 2.6 - #782


0.11 - 2014-05-21
-----------------

This release is not introducing a lot of features, and
focused on making Circus more robust & stable.

Major changes/fixes:

- Make sure we cannot execute two conflictings commands on the arbiter
  simultanously.
- we have 2 new streams class: TimedRotatingFileStream, WatchedFileStream
- we have one new hook: after_spawn hook
- CircusPlugin is easier to use
- fix autostart=False watchers during start (regression)

More changes:

- circus messages can be routed to syslog now - #748
- endpoint_owner option added so we can define which user owns ipc socket
  files created by circus.
- Started Windows support (just circusctl for now)
- fixed a lot of leaks in the tests
- Allow case sensitive environment variables
- The resource plugin now accepts absolute memory values - #609
- Add support to the add command for the 'singleton' option - #767
- Allow sending arbitrary signals to child procs via resource watcher - #756
- Allow INI/JSON/YAML configuration for logging
- Make sure we're compatible with psutil 2.x *and* 3.x
- Added more metrics to the statsd provider - #698
- Fixed multicast discovery - #731
- Make start, restart and reload more uniform - #673
- Correctly initialize all use groups - #635
- improved tests stability
- many, many more things....


0.10 - 2013-11-04
-----------------

Major changes:

- Now Python 3.2 & 3.3 compatible - #586
- Moved the core to a fully async model - #569
- Improved documentation - #622

More changes:

- Added stop_signal & stop_children - #594
- Make sure the watchdog plugin closes the sockets - #588
- Switched to ZMQ JSON parser
- IN not supported on all platforms - #573
- Allow global environment substitutions in any config section - #560
- Allow dashes in sections names - #546
- Now variables are expanded everywhere in the config - #554
- Added the CommandReloader plugin
- Added before_signal & after_signal hooks
- Allow flapping plugin to retry indefinitely
- Don't respawn procs when the watcher is stopping - #529 - #536
- Added a unique id for each client message - #517
- worker ids are now "slots" -
- Fixed the graceful shutdown behavior - #515
- Make sure we can add watchers even if the arbiter is not started - #503
- Make sure make sure we pop expired process - #510
- Make sure the set command can set several hooks
- Correctly support ipv6 sockets - #507
- Allow custom options for stdout_stream and stderr_stream - #495
- Added time_format for FileStream - #493
- Added new socket config option to bind to a specific interface by name


0.9.3 - 2013-09-04
------------------

- Make sure we can add watchers even if the arbiter is not started
- Make sure we pop expired process
- Make sure the set command can set one or several hooks
- Correctly support ipv6 sockets and improvments of CircusSockets
- Give path default value to prevent UnboundLocalError
- Added a test for multicast_endpoint existence in Controller initialization
- Not converting every string of digits to ints anymore
- Add tests
- No need for special cases when converting stdout_stream options
- also accept umask as an argument for consistency
- Allow custom options for stdout_stream and stderr_stream.
- Add new socket config option to bind to a specific interface by name
- Add time_format for FileStream + tests
- Update circus.upstart


0.9.2 - 2013-07-17
------------------

- When a PYTHONPATH is defined in a config file, it's loaded
  in sys.path so hooks can be located there - #477, #481
- Use a single argument for add_callback so it works with
  PyZMQ < 13.1.x - see #478


0.9 - 2013-07-16
----------------

- added [env] sections wildcards
- added global [env] secrtion
- fixed hidden exception when circus-web is not installed - #424
- make sure incr/decr commands really us the nb option - #421
- Fix watcher virtualenv site-packages not in PYTHONPATH
- make sure we dont try to remove more processes than 0 - #429
- updated bootstrap.py - #436
- fixed multiplatform separator in pythonpath virtualenv watcher
- refactored socket close function
- Ensure env sections are applied to all watchers - #437
- added the reloadconfig command
- added circus.green and removed gevent from the core - #441, #452
- silenced spurious stdout & warnings in the tests - #438
- $(circus.env.*) can be used for all options in the config now
- added a before_spawn hook
- correct the path of circusd in systemd service file - #450
- make sure we can change hooks and set streams via CLI - #455
- improved doc
- added a spawn_count stat in watcher
- added min_cpu and min_mem parameters in ResourceWatcher plugin
- added the FQDN information to the arbiter.


0.8.1 - 2013-05-28
------------------

* circusd-stats was choking on unix sockets - #415
* circusd-stats & circushttpd child processes stdout/stderr are now left open
  by default. Python <= 2.7.5 would choke in the logging module in case
  the 2/3 fds were closed - #415
* Now redirecting to /dev/null in the child process instead of closing.
  #417

0.8 - 2013-05-24
----------------

* Integrated log handlers into zmq io loop.
* Make redirector restartable and subsequently more robust.
* Uses zmq.green.eventloop when gevent is detected
* Added support for CIRCUSCTL_ENDPOINT environment variable to circusctl - #396
* util: fix bug in to_uid function - #397
* Remove handler on ioloop error - #398.
* Improved test coverage
* Deprecated the 'service' option for the ResourceWatcher plugin - #404
* removed psutil.error usage
* Added UDP discovery in circusd - #407
* Now allowing globs at arbitrary directory levels - #388
* Added the 'statd' configuration option - #408
* Add pidfile, logoutput and loglevel option to circus configuration file - #379
* Added a tutorial in the docs.
* make sure we're merging all sections when using include - #414
* added pipe_stdout, pipe_stderr, close_child_stderr & close_child_stdout
  options to the Process class
* added close_child_stderr & close_child_stdout options to the watcher


0.7.1 - 2013-05-02
------------------

* Fixed the respawn option - #382
* Make sure we use an int for the timeout - #380
* display the unix sockets as well -  #381
* Make sure it works with the latest pyzmq
* introduced a second syntax for the fd notation


0.7 - 2013-04-08
----------------

* Fix get_arbiter example to use a dict for the watchers argument. #304
* Add some troubleshooting documentation #323
* Add python buildout support
* Removed the gevent and the thread redirectors. now using the ioloop - fixes
  #346. Relates #340
* circus.web is now its own project
* removed the pyzmq patching
* Allow the watcher to be configured but not started #283
* Add an option to load a virtualenv site dir
* added on_demand watchers
* added doc about nginx+websockets #371
* now properly parsing the options list of each command #369
* Fixed circusd-stats events handling #372
* fixed the overflow issue in circus-top #378
* many more things...

0.6 - 2012-12-18
----------------


* Patching protocols name for sockets - #248
* Don't autoscale graphs. #240
* circusctl: add per command help, from docstrings #217
* Added workers hooks
* Added Debian package - #227
* Added Redis, HTTP Observer, Full stats & Resource plugins
* Now processes can have titles
* Added autocompletion
* Added process/watcher age in the webui
* Added SSH tunnel support
* Now using pyzmq.green
* Added upstart script & Varnish doc
* Added environment variables & sections
* Added unix sockets support
* Added the *respawn* option to have single-run watchers
* Now using tox in the tests
* Allow socket substitution in args
* New doc theme
* New rotation options for streams: max_bytes/backup_count


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
