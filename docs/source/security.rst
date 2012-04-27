.. _security:

Security
========

Circus is built on the top of the ZeroMQ library and comes with no security
at all.

There were no focus yet on protecting the Circus system from attacks on its
ports, and depending on how you run it, you are creating a potential security
hole in the system.

This section explains what Circus does on your system when you run it, and
a few recommandations if you want to protect your server.

You can also read http://www.zeromq.org/area:faq#toc5


TCP ports
---------

By default, Circus opens the following TCP ports on the local host:

- **5555** -- the port used to control circus via **circusctl**
- **5556** -- the port used for the Publisher/Subscriber channel.

These ports allow client apps to interact with your Circus system, and
depending on how your infrastructure is organized, you may want to protect
these ports via firewalls **or** to configure Circus to run using **IPC**
ports. When Configured using IPC, the commands must be run from the same
box, but no one can access them from outside unlike TCP.


uid and gid
-----------

By default, all processes started with Circus will be running with the
same user and group than **circusd**. Depending on the privileges the user
has on the system, you may not have access to all the features Circus provides.

For instance, some statistics features on the running processes require
privileges. Typically, if the CPU usage numbers you get using
the **stats** command are *0*, it means your user can't access the proc
files.

You may run **circusd** as root, to fix this, and set the **uid** and **gid**
values for each watcher to get all features.

But beware that running **circusd** as root exposes you to potential
privilege escalation bugs. While we're doing our best to avoid any bug,
running as root and facing a bug that performs unwanted actions on your
system may be an issue.

The best way to prevent this is to make sure that the system running
Circus is isolated (like a VM) **or** to run the whole system under
a controlled user.


circushttpd
-----------

The web application is not secured at all and once connected on a running
Circus, it can do anything and everything.

**Do not make it publicly available**

If you want to protect the access to the web panel, you can serve it
behind Nginx or Apache or any proxy-capable web server, than can
set up security.
