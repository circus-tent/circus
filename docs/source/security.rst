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
same user than **circusd**. Depending on the system access of the user,
you may not have access to all the features Circus provides. For instance,
some statistics features on the running processes require privileges.

You may run **circusd** as root, and set the **uid** and **gid** values
for each watcher to get all features.

In any case, beware that depending on the application you run with Circus,
even if the processes are executed under a unprivileged user, if the
**circusd** process is run as root, it's not impossible that a bug
introduces a privilege escalation issue.

The best way to prevent this issue is to make sure that the system where
you run Circus is isolated -- like a VM.

