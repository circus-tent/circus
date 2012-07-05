.. _why:

Why should I use Circus instead of X ?
--------------------------------------


1. **Circus simplifies your web stack process management**

   Circus knows how to manage processes *and* sockets, so you don't
   have to delegate web workers managment to a WGSI server.

   See :ref:`whycircussockets`


2. **Circus provides pub/sub and poll notifications via ZeroMQ**

  Circus has a :term:`pub/sub` channel you can subscribe to. This channel
  receives all events happening in Circus. For example, you can be
  notified when a process is :term:`flapping`, or build a client that
  triggers a warning when some processes are eating all the CPU or RAM.

  These events are sent via a ZeroMQ channel, which makes it different
  from the stdin stream Supervisord uses:

  - Circus sends events in a fire-and-forget fashion, so there's no
    need to manually loop through *all* listeners and maintain their
    states.
  - Subscribers can be located on a remote host.

  Circus also provides ways to get status updates via one-time polls
  on a req/rep channel. This means you can get your information without
  having to subscribe to a stream. The :ref:`cli` command provided by
  Circus uses this channel.

  See :ref:`examples`.


3. **Circus is (Python) developer friendly**

  While Circus can be driven entirely by a config file and the
  *circusctl* / *circusd* commands, it is easy to reuse all or part of
  the system to build your own custom process watcher in Python.

  Every layer of the system is isolated, so you can reuse independently:

  - the process wrapper (:class:`Process`)
  - the processes manager (:class:`Watcher`)
  - the global manager that runs several processes managers (:class:`Arbiter`)
  - and so on…


4. **Circus scales**

  One of the use cases of Circus is to manage thousands of processes without
  adding overhead -- we're dedicated to focus on this.


