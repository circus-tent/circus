"""handle the management of the zeromq messages"""
import json
import sys
import time
import traceback

from circus import logger
from circus import zmq
from circus.commands import get_commands
from circus.exc import MessageError
from circus.py3compat import string_types


NOT_SPECIFIED = 0
INVALID_JSON = 1
UNKNOWN_COMMAND = 2
MESSAGE_ERROR = 3
OS_ERROR = 4
COMMAND_ERROR = 5
BAD_MSG_DATA_ERROR = 6

commands = get_commands()


def error(reason="unknown", tb=None, errno=NOT_SPECIFIED):
    return {
        "status": "error",
        "reason": reason,
        "tb": tb,
        "time": time.time(),
        "errno": errno
    }


def ok(props=None):
    resp = {"status": "ok", "time": time.time()}
    if props:
        resp.update(props)
    return resp


class ProtocolError(Exception):

    def __init__(self, msg, error, cast, errno):
        self.error = error
        self.errno = errno


def parse_message(msg):
    """Take a job, check that it's valid (the command exists, it respects the
    right syntax etc) and return the command, its properties and a boolean
    telling if we want to send back a response (named "cast").
    """
    try:
        json_msg = json.loads(msg)
    except ValueError:
        return ProtocolError(msg, "json invalid", errno=INVALID_JSON)

    cmd_name = json_msg.get('command')
    properties = json_msg.get('properties', {})

    # if cast is true, we ignore the response.
    cast = json_msg.get('msg_type') == "cast"

    try:
        cmd = commands[cmd_name.lower()]
    except KeyError:
        error = "unknown command: %r" % cmd_name
        raise ProtocolError(msg, error, cast=cast, errno=UNKNOWN_COMMAND)

    try:
        cmd.validate(properties)
        return cmd, properties, cast
    except MessageError as e:
        raise ProtocolError(msg, str(e), cast=cast, errno=MESSAGE_ERROR)


def parse_response(resp):
    """Check that the response is a valid reponse."""
    if not isinstance(resp, (dict, list,)):
        raise InvalidResponse("server error", errno=BAD_MSG_DATA_ERROR)

    if isinstance(resp, list):
        resp = {"results": resp}

    return resp


def super_function(job):
    cid, msg = job
    try:
        cmd, properties, cast = parse_message(msg)
    except ProtocolError as e:
        e.send_error(cid)

    try:
        cmd.execute()
    except OSError as e:
        raise ProtocolError(msg, str(e), cast=cast, errno=OS_ERROR)
    except:
        exctype, value = sys.exc_info()[:2]
        tb = traceback.format_exc()
        reason = "command %r: %s" % (msg, value)
        logger.debug("error: command %r: %s\n\n%s", msg, value, tb)
        raise ProtocolError(reason, tb, errno=COMMAND_ERROR)


def send_error(self, cid, msg, reason="unknown", tb=None, cast=False,
               errno=NOT_SPECIFIED):
    resp = error(reason=reason, tb=tb, errno=errno)
    self.send_response(cid, msg, resp, cast=cast)


def send_ok(self, cid, msg, props=None, cast=False):
    resp = ok(props)
    self.send_response(cid, msg, resp, cast=cast)


def send_response(stream, cid,  msg, resp, cast=False):
    if cast:
        return

    if cid is None:
        return

    if not isinstance(resp, string_types):
        resp = json.dumps(resp)

    if isinstance(resp, unicode):
        resp = resp.encode('utf8')

    try:
        stream.send(cid, zmq.SNDMORE)
        stream.send(resp)
    except zmq.ZMQError as e:
        logger.debug("Received %r - Could not send back %r - %s", msg,
                     resp, str(e))
