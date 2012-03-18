import sys
import traceback
try:
    from queue import Queue, Empty  # NOQA
except ImportError:
    from Queue import Queue, Empty  # NOQA


import zmq
from zmq.eventloop import ioloop

from circus.commands import get_commands
from circus import logger
from circus.exc import MessageError
from circus.sighandler import SysHandler


class Controller(object):
    def __init__(self, stream, loop, trainer, endpoint, check_delay=1.0):
        self.stream = stream
        self.loop = loop
        self.trainer = trainer
        self.check_delay = check_delay * 1000
        self.jobs = Queue()

        # initialize the sys handler
        self.sys_hdl = SysHandler(self)

        # handle messages
        self.stream.on_recv(self.handle_message)

        # get registered commands
        self.commands = get_commands()

    def start(self):
        self.caller = ioloop.PeriodicCallback(self.wakeup, self.check_delay,
                self.loop)
        self.caller.start()

    def wakeup(self):
        job = None
        try:
            job = self.jobs.get(block=False)
        except Empty:
            pass

        if job is not None:
            self.dispatch(job)
        self.trainer.manage_shows()

    def add_job(self, cid, msg):
        self.jobs.put((cid, msg), False)
        self.wakeup()

    def handle_message(self, raw_msg):
        cid, msg = raw_msg
        msg = msg.strip()

        if not msg:
            self.send_response(cid, msg, "error: empty command")
        else:
            logger.debug("got message %s" % msg)
            self.add_job(cid, msg)

    def dispatch(self, job):
        cid, msg = job
        msg_parts = msg.split(" ")
        resp = ""

        cmd_name = msg_parts.pop(0)

        try:
            cmd = self.commands[cmd_name.lower()]
        except KeyError:
            error = "error: unknown command: %r" % cmd_name
            return self.send_response(cid, msg, error)

        try:
            resp = cmd.execute(self.trainer, msg_parts)
        except MessageError as e:
            resp = "error: %s" % str(e)
        except OSError as e:
            resp = "error: %s" % e

        except:
            exctype, value = sys.exc_info()[:2]
            tb = traceback.format_exc()
            resp = "error: command %r: %s" % (msg, value)
            logger.debug("error: command %r: %s\n\n%s" % (msg,
                value, tb))
            sys.exc_clear()

        if resp is None:
            resp = "ok"

        if not isinstance(resp, (str, buffer,)):
            msg = "msg %r tried to send a non-string: %s" % (msg,
                    str(resp))
            raise ValueError(msg)

        self.send_response(cid, msg, resp)

        if cmd_name.lower() == "quit":
            if cid is not None:
                self.stream.flush()
            self.trainer.terminate()

    def send_response(self, cid,  msg, resp):
        if cid is None:
            return

        try:
            self.stream.send(cid, zmq.SNDMORE)
            self.stream.send(resp)
        except zmq.ZMQError as e:
            logger.info("Received %r - Could not send back %r - %s" %
                                (msg, resp, str(e)))

    def stop(self):
        self.caller.stop()
