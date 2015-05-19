circus-plugin man page
######################

Synopsis
--------

circus-plugin [options] [plugin]


Description
-----------

circus-plugin allows to launch a plugin from a running Circus daemon.


Arguments
---------

:plugin: Fully qualified name of the plugin class.
	 

Options
-------

:--endpoint *ENDPOINT*:
   Connection endpoint.

:--pubsub *PUBSUB*:
   The circusd ZeroMQ pub/sub socket to connect to.

:--config *CONFIG*: The plugin configuration file.

:--check-delay *CHECK_DELAY*: Check delay.
		    
:\--log-level *LEVEL*:
   Specify the log level. *LEVEL* can be `info`, `debug`, `critical`,
   `warning` or `error`.

:\--log-output *LOGOUTPUT*:
   The location where the logs will be written. The default behavior is to
   write to stdout (you can force it by passing '-' to this option). Takes
   a filename otherwise.

:--ssh *SSH*:
   SSH Server in the format ``user@host:port``.

:-h, \--help:
   Show the help message and exit.

:\--version:
   Displays Circus version and exits.


See also
--------

`circus` (1), `circusd` (1), `circusctl` (1), `circusd-stats` (1), `circus-top` (1).

Full Documentation is available at http://circus.readthedocs.org
