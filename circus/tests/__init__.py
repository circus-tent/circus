

def setUp():
    from circus import _patch   # NOQA
    try:
        import gevent                   # NOQA
        from gevent import monkey       # NOQA
        try:
            import zmq.eventloop as old_io
            import zmq.green as zmq         # NOQA
            old_io.ioloop.Poller = zmq.Poller
        except ImportError:
            # older version
            try:
                from gevent_zeromq import (                     # NOQA
                        monkey_patch, IOLOOP_IS_MONKEYPATCHED)  # NOQA
                monkey_patch()
                warnings.warn("gevent_zeromq is deprecated, please "
                            "use PyZMQ >= 2.2.0.1")
            except ImportError:
                raise ImportError(_MSG)

        monkey.patch_all()
    except ImportError:
        pass
