import sys
import traceback
try:
    from queue import Queue, Empty  # NOQA
except ImportError:
    from Queue import Queue, Empty  # NOQA

from urlparse import urlparse

import zmq
from zmq.utils.jsonapi import jsonmod as json
from zmq.eventloop import ioloop, zmqstream

from circus.util import create_udp_socket
from circus.commands import get_commands, ok, error, errors
from circus import logger
from circus.exc import MessageError
from circus.py3compat import string_types
from circus.sighandler import SysHandler


class Controller(object):

    def __init__(self, endpoint, multicast_endpoint, context, loop, arbiter,
                 check_delay=1.0):
        self.arbiter = arbiter
        self.endpoint = endpoint
        self.multicast_endpoint = multicast_endpoint
        self.context = context
        self.loop = loop
        self.check_delay = check_delay * 1000
        self.started = False

        self.jobs = Queue()

        # initialize the sys handler
        self._init_syshandler()

        # get registered commands
        self.commands = get_commands()

    def _init_syshandler(self):
        self.sys_hdl = SysHandler(self)

    def _init_stream(self):
        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def initialize(self):
        # initialize controller

        # Initialize ZMQ Sockets
        self.ctrl_socket = self.context.socket(zmq.ROUTER)
        self.ctrl_socket.bind(self.endpoint)
        self.ctrl_socket.linger = 0
        self._init_stream()

        # Initialize UDP Socket
        multicast_addr, multicast_port = urlparse(self.multicast_endpoint)\
            .netloc.split(':')
        self.udp_socket = create_udp_socket(multicast_addr, multicast_port)
        self.loop.add_handler(self.udp_socket.fileno(),
                              self.handle_autodiscover_message,
                              ioloop.IOLoop.READ)

    def start(self):
        self.initialize()
        self.caller = ioloop.PeriodicCallback(self.wakeup, self.check_delay,
                                              self.loop)
        self.caller.start()
        self.started = True

    def stop(self):
        if self.started:
            self.caller.stop()
            try:
                self.stream.flush()
                self.stream.close()
            except (IOError, zmq.ZMQError):
                pass
            self.ctrl_socket.close()
        self.sys_hdl.stop()

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
        """Each time we receive a message on the zmq endpoint, check that the
        command is not empty and add a job for it.

        """
        cid, msg = raw_msg
        msg = msg.strip()

        if not msg:
            self.send_response(cid, msg, "error: empty command")
        else:
            logger.debug("got message %s", msg)
            self.add_job(cid, msg)

    def handle_autodiscover_message(self, fd_no, type):
        data, address = self.udp_socket.recvfrom(1024)
        data = json.loads(data)
        self.udp_socket.sendto(json.dumps({'endpoint': self.endpoint}),
                               address)

    def dispatch(self, job):
        cid, msg = job
        try:
            cmd, properties, cast = parse_message(msg)
        except InvalidMessage as e:
            return send_error(cid, msg, e.error, cast=cast, errno=e.errno)

        try:
            cmd.execute()
        except OSError as e:
            return send_error(cid, msg, str(e), cast=cast, errno=OS_ERROR)
        except:
            exctype, value = sys.exc_info()[:2]
            tb = traceback.format_exc()
            reason = "command %r: %s" % (msg, value)
            logger.debug("error: command %r: %s\n\n%s", msg, value, tb)
            raise InvalidMessage(msg, reason, tb, cast=cast, errno=COMMAND_ERROR)

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
            error_ = "unknown command: %r" % cmd_name
            return self.send_error(cid, msg, error_, cast=cast,
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
            msg = "msg %r tried to send a non-dict: %s" % (msg, str(resp))
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

    def send_response(self, cid, msg, resp, cast=False):
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
