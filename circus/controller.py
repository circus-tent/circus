import os
import sys
import traceback
import functools
from queue import Queue, Empty  # noqa: F401
from urllib.parse import urlparse


import zmq
import zmq.utils.jsonapi as json
from tornado import ioloop
from zmq.eventloop import zmqstream
from tornado.concurrent import Future

from circus.util import create_udp_socket
from circus.util import check_future_exception_and_log
from circus.util import to_uid
from circus.commands import get_commands, ok, error, errors
from circus import logger
from circus.exc import MessageError, ConflictError
from circus.sighandler import SysHandler


class Controller(object):

    def __init__(self, endpoint, multicast_endpoint, context, loop, arbiter,
                 check_delay=1.0, endpoint_owner=None):
        self.arbiter = arbiter
        self.caller = None
        self.endpoint = endpoint
        self.multicast_endpoint = multicast_endpoint
        self.context = context
        self.loop = loop
        self.check_delay = check_delay * 1000
        self.endpoint_owner = endpoint_owner
        self.started = False
        self._managing_watchers_future = None

        # initialize the sys handler
        self._init_syshandler()

        # get registered commands
        self.commands = get_commands()

    def _init_syshandler(self):
        self.sys_hdl = SysHandler(self)

    def _init_stream(self):
        self.stream = zmqstream.ZMQStream(self.ctrl_socket, self.loop)
        self.stream.on_recv(self.handle_message)

    def _init_multicast_endpoint(self):
        multicast_addr, multicast_port = urlparse(self.multicast_endpoint)\
            .netloc.split(':')
        try:
            self.udp_socket = create_udp_socket(multicast_addr,
                                                multicast_port)
            self.loop.add_handler(self.udp_socket.fileno(),
                                  self.handle_autodiscover_message,
                                  ioloop.IOLoop.READ)
        except (IOError, OSError, ValueError):
            message = ("Multicast discovery is disabled, there was an "
                       "error during udp socket creation.")
            logger.warning(message, exc_info=True)

    @property
    def endpoint_owner_mode(self):
        return self.endpoint_owner is not None and \
            self.endpoint.startswith('ipc://')

    def initialize(self):
        # initialize controller

        # Initialize ZMQ Sockets
        self.ctrl_socket = self.context.socket(zmq.ROUTER)
        self.ctrl_socket.bind(self.endpoint)
        self.ctrl_socket.linger = 0

        # support chown'ing the zmq endpoint on unix platforms
        if self.endpoint_owner_mode:
            uid = to_uid(self.endpoint_owner)
            sockpath = self.endpoint[6:]  # length of 'ipc://' prefix
            os.chown(sockpath, uid, -1)

        self._init_stream()

        # Initialize UDP Socket
        if self.multicast_endpoint:
            self._init_multicast_endpoint()

    def manage_watchers(self):
        if self._managing_watchers_future is not None:
            logger.debug("manage_watchers is already running...")
            return
        try:
            self._managing_watchers_future = self.arbiter.manage_watchers()
            self.loop.add_future(self._managing_watchers_future,
                                 self._manage_watchers_cb)
        except ConflictError:
            logger.debug("manage_watchers is conflicting with another command")

    def _manage_watchers_cb(self, future):
        self._managing_watchers_future = None

    def start(self):
        self.initialize()
        if self.check_delay > 0:
            # The specific case (check_delay < 0)
            # so with no period callback to manage_watchers
            # is probably "unit tests only"
            self.caller = ioloop.PeriodicCallback(self.manage_watchers,
                                                  self.check_delay)
            self.caller.start()
        self.started = True

    def stop(self):
        if self.started:
            if self.caller is not None:
                self.caller.stop()
            try:
                self.stream.flush()
                self.stream.close()
            except (IOError, zmq.ZMQError):
                pass
            self.ctrl_socket.close()
        self.sys_hdl.stop()

    def handle_message(self, raw_msg):
        cid, msg = raw_msg
        msg = msg.strip()

        if not msg:
            self.send_response(None, cid, msg, "error: empty command")
        else:
            logger.debug("got message %s", msg)
            self.dispatch((cid, msg))

    def handle_autodiscover_message(self, fd_no, type):
        __, address = self.udp_socket.recvfrom(1024)
        self.udp_socket.sendto(json.dumps({'endpoint': self.endpoint}),
                               address)

    def _dispatch_callback_future(self, msg, cid, mid, cast, cmd_name,
                                  send_resp, future):
        exception = check_future_exception_and_log(future)
        if exception is not None:
            if send_resp:
                self.send_error(mid, cid, msg, "server error", cast=cast,
                                errno=errors.BAD_MSG_DATA_ERROR)
        else:
            resp = future.result()
            if send_resp:
                self._dispatch_callback(msg, cid, mid, cast, cmd_name, resp)

    def _dispatch_callback(self, msg, cid, mid, cast, cmd_name, resp=None):
        if resp is None:
            resp = ok()

        if not isinstance(resp, (dict, list)):
            msg = "msg %r tried to send a non-dict: %s" % (msg, str(resp))
            logger.error("msg %r tried to send a non-dict: %s", msg, str(resp))
            return self.send_error(mid, cid, msg, "server error", cast=cast,
                                   errno=errors.BAD_MSG_DATA_ERROR)

        if isinstance(resp, list):
            resp = {"results": resp}

        self.send_ok(mid, cid, msg, resp, cast=cast)

        if cmd_name.lower() == "quit":
            if cid is not None:
                self.stream.flush()

    def dispatch(self, job, future=None):
        cid, msg = job
        try:
            json_msg = json.loads(msg)
        except ValueError:
            return self.send_error(None, cid, msg, "json invalid",
                                   errno=errors.INVALID_JSON)

        mid = json_msg.get('id')
        cmd_name = json_msg.get('command')
        properties = json_msg.get('properties', {})
        cast = json_msg.get('msg_type') == "cast"

        try:
            cmd = self.commands[cmd_name.lower()]
        except KeyError:
            error_ = "unknown command: %r" % cmd_name
            return self.send_error(mid, cid, msg, error_, cast=cast,
                                   errno=errors.UNKNOWN_COMMAND)

        try:
            cmd.validate(properties)
            resp = cmd.execute(self.arbiter, properties)
            if isinstance(resp, Future):
                if properties.get('waiting', False):
                    cb = functools.partial(self._dispatch_callback_future, msg,
                                           cid, mid, cast, cmd_name, True)
                    resp.add_done_callback(cb)
                else:
                    cb = functools.partial(self._dispatch_callback_future, msg,
                                           cid, mid, cast, cmd_name, False)
                    resp.add_done_callback(cb)
                    self._dispatch_callback(msg, cid, mid, cast,
                                            cmd_name, None)
            else:
                self._dispatch_callback(msg, cid, mid, cast,
                                        cmd_name, resp)
        except MessageError as e:
            return self.send_error(mid, cid, msg, str(e), cast=cast,
                                   errno=errors.MESSAGE_ERROR)
        except ConflictError as e:
            if self._managing_watchers_future is not None:
                logger.debug("the command conflicts with running "
                             "manage_watchers, re-executing it at "
                             "the end")
                cb = functools.partial(self.dispatch, job)
                self.loop.add_future(self._managing_watchers_future, cb)
                return
            # conflicts between two commands, sending error...
            return self.send_error(mid, cid, msg, str(e), cast=cast,
                                   errno=errors.COMMAND_ERROR)
        except OSError as e:
            return self.send_error(mid, cid, msg, str(e), cast=cast,
                                   errno=errors.OS_ERROR)
        except:  # noqa: E722
            exctype, value = sys.exc_info()[:2]
            tb = traceback.format_exc()
            reason = "command %r: %s" % (msg, value)
            logger.debug("error: command %r: %s\n\n%s", msg, value, tb)
            return self.send_error(mid, cid, msg, reason, tb, cast=cast,
                                   errno=errors.COMMAND_ERROR)

    def send_error(self, mid, cid, msg, reason="unknown", tb=None, cast=False,
                   errno=errors.NOT_SPECIFIED):
        resp = error(reason=reason, tb=tb, errno=errno)
        self.send_response(mid, cid, msg, resp, cast=cast)

    def send_ok(self, mid, cid, msg, props=None, cast=False):
        resp = ok(props)
        self.send_response(mid, cid, msg, resp, cast=cast)

    def send_response(self, mid, cid, msg, resp, cast=False):
        if cast:
            return

        if cid is None:
            return

        if isinstance(resp, str):
            raise DeprecationWarning('Takes only a mapping')

        resp['id'] = mid
        resp = json.dumps(resp)

        logger.debug("sending response %s", resp)

        try:
            self.stream.send(cid, zmq.SNDMORE)
            self.stream.send(resp)
        except (IOError, zmq.ZMQError) as e:
            logger.debug("Received %r - Could not send back %r - %s", msg,
                         resp, str(e))
