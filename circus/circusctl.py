# -*- coding: utf-8 -

import argparse
import getopt
import json
import sys
import traceback

# import pygments if here
try:
    import pygments     # NOQA
    from pygments.lexers import get_lexer_for_mimetype
    from pygments.formatters import TerminalFormatter
except ImportError:
    pygments = False    # NOQA

from circus.client import CircusClient
from circus.consumer import CircusConsumer
from circus.commands import get_commands
from circus.exc import CallError, ArgumentError
from circus.util import DEFAULT_ENDPOINT_SUB, DEFAULT_ENDPOINT_DEALER




def prettify(jsonobj, prettify=True):
    """ prettiffy JSON output """
    if not prettify:
        return json.dumps(jsonobj)

    json_str = json.dumps(jsonobj, indent=2, sort_keys=True)
    if pygments:
        try:
            lexer = get_lexer_for_mimetype("application/json")
            return pygments.highlight(json_str, lexer, TerminalFormatter())
        except:
            pass

    return json_str


def _get_switch_str(opt):
    """
    Output just the '-r, --rev [VAL]' part of the option string.
    """
    if opt[2] is None or opt[2] is True or opt[2] is False:
        default = ""
    else:
        default = "[VAL]"
    if opt[0]:
        # has a short and long option
        return "-%s, --%s %s" % (opt[0], opt[1], default)
    else:
        # only has a long option
        return "--%s %s" % (opt[1], default)


class ControllerApp(object):

    def __init__(self):
        self.commands = get_commands()
        self.options = {
            'endpoint' : {'default' : None, 'help' : 'connection endpoint'},
            'timeout' : {'default' : 5, 'help' : 'connection timeout'},
            'json' : {'default' : False, 'action' : 'store_true', 'help' : 'output to JSON'},
            'prettify' : {'default' : False, 'action' : 'store_true', 'help' : 'prettify output'},
            'version' : {'default': False, 'action' : 'store_true', 'help' : 'display version and exit'}
        }

    def run(self, args):
        try:
            sys.exit(self.dispatch(args))
        except getopt.GetoptError as e:
            print("Error: %s\n" % str(e))
            self.display_help()
            sys.exit(2)
        except CallError as e:
            sys.stderr.write("%s\n" % str(e))
            sys.exit(1)
        except ArgumentError as e:
            sys.stderr.write("%s\n" % str(e))
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception, e:
            sys.stderr.write(traceback.format_exc())
            sys.exit(1)

    def get_globalopts(self, args):
        globalopts = {}
        for option in self.options:
            globalopts[option] = getattr(args, option)
        return globalopts

    def dispatch(self, args):
        parser = argparse.ArgumentParser()
        for option in self.options:
            parser.add_argument('--' + option, **self.options[option])
        parser.add_argument('command', nargs="?")
        parser.add_argument('args', nargs="*")

        args = parser.parse_args()
        globalopts = self.get_globalopts(args)
        opts = {}

        if args.version:
            return self.display_version()
        else:
            if args.command not in self.commands:
                raise ArgumentError('Unknown command %r' % args.command)
            else:
                cmd = self.commands[args.command]
                if args.endpoint is None:
                    if cmd.msg_type == 'sub':
                        args.endpoint = DEFAULT_ENDPOINT_SUB
                    else:
                        args.endpoint = DEFAULT_ENDPOINT_DEALER
                msg = cmd.message(*args.args, **opts)
                return getattr(self, "handle_%s" % cmd.msg_type)(cmd, globalopts,
                    msg, args.endpoint, int(args.timeout))

    def display_version(self, *args, **opts):
        from circus import __version__
        print(__version__)
        return 0

    def handle_sub(self, cmd, opts, topics, endpoint, timeout):
        consumer = CircusConsumer(topics, endpoint=endpoint)
        for topic, msg in consumer:
            print("%s: %s" % (topic, msg))
        return 0

    def _console(self, client, cmd, opts, msg):
        if opts['json']:
            return prettify(client.call(msg), prettify=opts['prettify'])
        else:
            return cmd.console_msg(client.call(msg))

    def handle_dealer(self, cmd, opts, msg, endpoint, timeout):
        client = CircusClient(endpoint=endpoint, timeout=timeout)
        try:
            if isinstance(msg, list):
                for i, command in enumerate(msg):
                    clm = self._console(client, command['cmd'], opts,
                                        command['msg'])
                    print("%s: %s" % (i, clm))
            else:
                print(self._console(client, cmd, opts, msg))
        except CallError as e:
            sys.stderr.write(str(e) + " Try to raise the --timeout value\n")
            return 1
        finally:
            client.stop()
        return 0

def main():
    controller = ControllerApp()
    controller.run(sys.argv[1:])

if __name__ == '__main__':
    main()
