import sys
import traceback
try:
    from queue import Queue, Empty  # NOQA
except ImportError:
    from Queue import Queue, Empty  # NOQA


from circus import zmq
from zmq.eventloop import ioloop, zmqstream
from zmq.utils.jsonapi import jsonmod as json

from circus.commands import get_commands, ok, error, errors
from circus import logger
from circus.exc import MessageError
from circus.py3compat import string_types
from circus.sighandler import SysHandler


class Controller(object):
    def __init__(self, endpoint, context, loop, arbiter, check_delay=1.0):
        self.arbiter = arbiter
        self.endpoint = endpoint
        self.context = context
        self.loop = loop
        self.check_delay = check_delay * 1000

        self.jobs = Queue()

        # initialize the sys handler
        self.sys_hdl = SysHandler(self)

        # get registered commands
        self.commands = get_commands()

    def initialize(self):
        # initialize controller
        self.ctrl_socket = self.context.socket(zmq.ROUTER)
        self.ctrl_socket.bind(self.endpoint)
        self.ctrl_socket.linger = 0

        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def start(self):
        self.initialize()
        self.caller = ioloop.PeriodicCallback(self.wakeup, self.check_delay,
                self.loop)
        self.caller.start()

    def stop(self):
        self.caller.stop()
        self.ctrl_socket.close()

    def wakeup(self):
        job = None
        try:
            job = self.jobs.get(block=False)
        except Empty:
            pass

        if job is not None:
            self.dispatch(job)
        self.arbiter.manage_watchers()

    def add_job(self, cid, msg):
        self.jobs.put((cid, msg), False)
        self.wakeup()

    def handle_message(self, raw_msg):
        cid, msg = raw_msg
        msg = msg.strip()

        if not msg:
            self.send_response(cid, msg, "error: empty command")
        else:
            logger.debug("got message %s", msg)
            self.add_job(cid, msg)

    def dispatch(self, job):
        cid, msg = job

        try:
            json_msg = json.loads(msg)
        except ValueError:
            return self.send_error(cid, msg, "json invalid",
                                   errno=errors.INVALID_JSON)

        cmd_name = json_msg.get('command')
        properties = json_msg.get('properties', {})
        cast = json_msg.get('msg_type') == "cast"

        try:
            cmd = self.commands[cmd_name.lower()]
        except KeyError:
            error = "unknown command: %r" % cmd_name
            return self.send_error(cid, msg, error, cast=cast,
                        errno=errors.UNKNOWN_COMMAND)

        try:
            cmd.validate(properties)
            resp = cmd.execute(self.arbiter, properties)
        except MessageError as e:
            return self.send_error(cid, msg, str(e), cast=cast,
                    errno=errors.MESSAGE_ERROR)
        except OSError as e:
            return self.send_error(cid, msg, str(e), cast=cast,
                    errno=errors.OS_ERROR)
        except:
            exctype, value = sys.exc_info()[:2]
            tb = traceback.format_exc()
            reason = "command %r: %s" % (msg, value)
            logger.debug("error: command %r: %s\n\n%s", msg, value, tb)
            return self.send_error(cid, msg, reason, tb, cast=cast,
                    errno=errors.COMMAND_ERROR)

        if resp is None:
            resp = ok()

        if not isinstance(resp, (dict, list,)):
            msg = "msg %r tried to send a non-dict: %s" % (msg,
                    str(resp))
            logger.error("msg %r tried to send a non-dict: %s", msg, str(resp))
            return self.send_error(cid, msg, "server error", cast=cast,
                    errno=errors.BAD_MSG_DATA_ERROR)

        if isinstance(resp, list):
            resp = {"results": resp}

        self.send_ok(cid, msg, resp, cast=cast)

        if cmd_name.lower() == "quit":
            if cid is not None:
                self.stream.flush()

            self.arbiter.stop()

    def send_error(self, cid, msg, reason="unknown", tb=None, cast=False,
                   errno=errors.NOT_SPECIFIED):
        resp = error(reason=reason, tb=tb, errno=errno)
        self.send_response(cid, msg, resp, cast=cast)

    def send_ok(self, cid, msg, props=None, cast=False):
        resp = ok(props)
        self.send_response(cid, msg, resp, cast=cast)

    def send_response(self, cid,  msg, resp, cast=False):
        if cast:
            return

        if cid is None:
            return

        if not isinstance(resp, string_types):
            resp = json.dumps(resp)

        if isinstance(resp, unicode):
            resp = resp.encode('utf8')

        try:
            self.stream.send(cid, zmq.SNDMORE)
            self.stream.send(resp)
        except zmq.ZMQError as e:
            logger.debug("Received %r - Could not send back %r - %s", msg,
                         resp, str(e))
