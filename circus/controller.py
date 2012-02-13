import os
import tempfile
import zmq

from circus.sighandler import SysHandler


class Controller(object):
    def __init__(self, endpoint, trainer, timeout=1.0, ipc_prefix=None):
        self.context = zmq.Context()

        self.skt = self.context.socket(zmq.REP)
        self.skt.bind(endpoint)

        # bind the socket to internal ipc.
        ipc_name = "circus-ipc-%s" % os.getpid()
        if not ipc_prefix:
            ipc_prefix = tempfile.gettempdir()
        ipc_path = os.path.join(os.path.dirname(ipc_prefix), ipc_name)
        self.skt.bind("ipc://%s" % ipc_path)

        self.poller = zmq.Poller()
        self.poller.register(self.skt, zmq.POLLIN)

        self.trainer = trainer
        self.timeout = timeout * 1000

        # start the sys handler
        self.sys_hdl = SysHandler(ipc_path)

    def poll(self):
        try:
            events = dict(self.poller.poll(self.timeout))
        except zmq.ZMQError:
            return

        for socket in events:
            msg = socket.recv() or ""
            msg = msg.lower().strip()
            if not msg:
                socket.send("error: empty command")
                continue

            msg_parts = msg.split(" ")

            if len(msg_parts) > 1 and msg_parts[1]:
                # program command
                # a program command passed with the format
                # COMMAND PROGRAM ARGS

                try:
                    program = self.trainer.get_program(msg_parts[1])
                    cmd = msg_parts[0].lower()

                    if len(msg_parts)> 2:
                        args = msg_parts[2:]
                    else:
                        args = []

                    try:
                        handler = getattr(program, "handle_%s" % cmd)
                        ret = handler(*args)
                        socket.send(ret)
                    except AttributeError:
                        socket.send("error: ignored messaged %r" % msg)
                    except Exception, e:
                        socket.send("error: command %r: %s" %
                                (msg, str(e)))
                except IndexError:
                    socket.send("error: program %s not found" % msg_parts[1])
            else:
                # trainer commands
                if msg == 'numworkers':
                    socket.send(str(self.trainer.num_workers()))
                elif msg == 'programs':
                    socket.send(self.trainer.list_programs())
                else:
                    try:
                        handler = getattr(self.trainer, "handle_%s" % msg)
                        ret = handler()
                        socket.send(ret)
                    except AttributeError:
                        socket.send("error: ignored messaged %r" % msg)

    def terminate(self):
        self.sys_hdl.terminate()
        try:
            self.context.destroy(0)
        except:
            pass
