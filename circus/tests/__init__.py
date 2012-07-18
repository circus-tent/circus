

def setUp():
    from circus import _patch   # NOQA
    try:
        from gevent import monkey       # NOQA
        try:
            from gevent_zeromq import monkey_patch, IOLOOP_IS_MONKEYPATCHED  # NOQA
            monkey.patch_all()
            monkey_patch()
        except ImportError:
            msg = """We have detected that you have gevent in your
            environment. In order to have Circus working, you *must*
            install gevent_zmq from :

            https://github.com/tarekziade/gevent-zeromq

            Circus will not need this in the future once
            pyzmq gets a green poller:

            https://github.com/zeromq/pyzmq/issues/197
            """
            raise ImportError(msg)
    except ImportError:
        pass
