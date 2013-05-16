try:
    import gevent       # NOQA
    from zmq.green.eventloop import ioloop, zmqstream   # NOQA
except ImportError:
    from zmq.eventloop import ioloop, zmqstream         # NOQA
