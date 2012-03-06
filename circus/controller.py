import os
import tempfile
import traceback
import zmq

from circus.exc import AlreadyExist
from circus.sighandler import SysHandler
from circus.show import Show

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
        self.sys_hdl = SysHandler(trainer)

    def poll(self):
        try:
            events = dict(self.poller.poll(self.timeout))
        except zmq.ZMQError, e:
            return

        for socket in events:
            msg = socket.recv() or ""
            msg = msg.lower().strip()
            if not msg:
                socket.send("error: empty command")
                continue

            msg_parts = msg.split(" ")

            resp = ""
            if len(msg_parts) > 1 and msg_parts[1]:
                # program command
                # a program command passed with the format
                # COMMAND PROGRAM ARGS

                cmd = msg_parts[0].lower()

                if cmd == "add_show":
                    if len(msg_parts) < 3:
                        resp = "error: invalid number of parameters"
                    else:
                        show_cmd = " ".join(msg_parts[2:])
                        show = Show(msg_parts[1], show_cmd, stopped=True)
                        try:
                            self.trainer.add_show(show)
                            resp = "ok"
                        except OSError, e:
                            resp = "error: %s" % str(e)
                        except AlreadyExist, e:
                            resp = "error: %s" % str(e)

                elif cmd == "del_show":
                    try:
                        self.trainer.del_show(msg_parts[1])
                        resp = "ok"
                    except KeyError:
                        resp = "error: program %s not found" % msg_parts[1]
                else:
                    try:
                        program = self.trainer.get_show(msg_parts[1])

                        if len(msg_parts) > 2:
                            args = msg_parts[2:]
                        else:
                            args = []

                        try:
                            handler = getattr(program, "handle_%s" % cmd)
                            resp = handler(*args)
                        except AttributeError:
                            resp = "error: ignored messaged %r" % msg
                        except OSError, e:
                            resp = "error: %s" % str(e)
                        except Exception, e:
                            tb = traceback.format_exc()
                            resp = "error: command %r: %s [%s]" % (msg,
                                    str(e), tb)
                    except KeyError:
                        resp = "error: program %s not found" % msg_parts[1]
            else:
                # trainer commands
                if msg == 'numflies':
                    resp = str(self.trainer.num_flies())
                elif msg == 'numshows':
                    resp = str(self.trainer.num_shows())
                elif msg in ('quit', 'halt',):
                    socket.send("ok")
                    return self.trainer.stop()
                else:
                    try:
                        handler = getattr(self.trainer, "handle_%s" % msg)
                        resp = handler()
                    except OSError, e:
                        resp = "error: %s" % str(e)
                    except AttributeError:
                        resp = "error: ignored messaged %r" % msg
                    except Exception, e:
                        tb = traceback.format_exc()
                        resp = "error: command %r: %s [%s]" % (msg,
                                str(e), tb)

            if resp is None:
                continue

            if not isinstance(resp, (str, buffer,)):
                msg = "msg %r tried to send a non-string: %s" % (msg,
                        str(resp))
                raise ValueError(msg)

            socket.send(resp)

    def stop(self):
        try:
            self.context.destroy(0)
        except:
            pass
