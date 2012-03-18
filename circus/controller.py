import errno
import os
import sys
import tempfile
import traceback

import zmq

from circus.commands import get_commands
from circus import logger
from circus.exc import AlreadyExist, MessageError
from circus.show import Show


class Controller(object):
    def __init__(self, socket, trainer, timeout=1.0):
        self.socket = socket
        self.trainer = trainer
        self.timeout = timeout * 1000

        # get registered commands
        self.commands = get_commands()

    def start(self):
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def poll(self):
        while True:
            try:
                events = dict(self.poller.poll(self.timeout))
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    return
            else:
                break

        for client in events:
            _id = client.recv()
            msg = client.recv() or ""
            msg = msg.strip()
            if not msg:
                self.send_response(_id, client, msg,
                        "error: empty command")
                continue

            logger.debug("got message %s" % msg)
            msg_parts = msg.split(" ")
            resp = ""

            cmd_name = msg_parts.pop(0)

            try:
                cmd = self.commands[cmd_name.lower()]
            except KeyError:
                error = "error: unknown command: %r" % cmd_name
                return self.send_response(_id, client, msg, error)

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

            self.send_response(_id, client, msg, resp)

            if cmd_name.lower() == "quit":
                self.trainer.terminate()

    def send_response(self, client_id, sock, msg, resp):
        try:
            sock.send(client_id, zmq.SNDMORE)
            sock.send(resp)
        except zmq.ZMQError as e:
            logger.error("Received %r - Could not send back %r - %s" %
                                (msg, resp, str(e)))


