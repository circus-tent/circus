# -*- coding: utf-8 -
import argparse
import cmd
import getopt
import json
import logging
import os
import sys
import textwrap
import traceback
import shlex

# import pygments if here
try:
    import pygments     # NOQA
    from pygments.lexers import get_lexer_for_mimetype
    from pygments.formatters import TerminalFormatter
except ImportError:
    pygments = False    # NOQA

from circus import __version__
from circus.client import CircusClient
from circus.commands import get_commands
from circus.consumer import CircusConsumer
from circus.exc import CallError, ArgumentError
from circus.util import DEFAULT_ENDPOINT_SUB, DEFAULT_ENDPOINT_DEALER


USAGE = 'circusctl [options] command [args]'
VERSION = 'circusctl ' + __version__
TIMEOUT_MSG = """\

A time out usually happens in one of those cases:

#1 The Circus daemon could not be reached.
#2 The Circus daemon took too long to perform the operation

For #1, make sure you are hitting the right place
by checking your --endpoint option.

For #2, if you are not expecting a result to
come back, increase your timeout option value
(particularly with waiting switches)
"""


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


class _Help(argparse.HelpFormatter):

    commands = None

    def _metavar_formatter(self, action, default_metavar):
        if action.dest != 'command':
            return super(_Help, self)._metavar_formatter(action,
                                                         default_metavar)

        commands = sorted(self.commands.items())
        max_len = max([len(name) for name, help in commands])

        output = []
        for name, cmd in commands:
            output.append('\t%-*s\t%s' % (max_len, name, cmd.short))

        def format(tuple_size):
            res = '\n'.join(output)
            return (res, ) * tuple_size

        return format

    def start_section(self, heading):
        if heading == 'positional arguments':
            heading = 'Commands'
        super(_Help, self).start_section(heading)


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

    def __init__(self, commands, client=None):
        self.commands = commands
        self.client = client

    def run(self, args):
        try:
            return self.dispatch(args)
        except getopt.GetoptError as e:
            print("Error: %s\n" % str(e))
            self.display_help()
            return 2
        except CallError as e:
            sys.stderr.write("%s\n" % str(e))
            return 1
        except ArgumentError as e:
            sys.stderr.write("%s\n" % str(e))
            return 1
        except KeyboardInterrupt:
            return 1
        except Exception:
            sys.stderr.write(traceback.format_exc())
            return 1

    def dispatch(self, args):
        opts = {}
        cmd = self.commands[args.command]
        for option in cmd.options:
            name = option[1]
            if name in args:
                opts[name] = getattr(args, name)

        if args.help:
            print(textwrap.dedent(cmd.__doc__))
            return 0
        else:
            if hasattr(args, 'start'):
                opts['start'] = args.start

            if args.endpoint is None and cmd.msg_type != 'dealer':
                if cmd.msg_type == 'sub':
                    args.endpoint = DEFAULT_ENDPOINT_SUB
                else:
                    args.endpoint = DEFAULT_ENDPOINT_DEALER

            msg = cmd.message(*args.args, **opts)
            handler = getattr(self, "handle_%s" % cmd.msg_type)
            return handler(cmd, self.globalopts, msg, args.endpoint,
                           int(args.timeout), args.ssh, args.ssh_keyfile)

    def handle_sub(self, cmd, opts, topics, endpoint, timeout, ssh_server,
                   ssh_keyfile):
        consumer = CircusConsumer(topics, endpoint=endpoint)
        for topic, msg in consumer:
            print("%s: %s" % (topic, msg))
        return 0

    def _console(self, client, cmd, opts, msg):
        if opts['json']:
            return prettify(client.call(msg), prettify=opts['prettify'])
        else:
            return cmd.console_msg(client.call(msg))

    def handle_dealer(self, cmd, opts, msg, endpoint, timeout, ssh_server,
                      ssh_keyfile):
        if endpoint is not None:
            client = CircusClient(endpoint=endpoint, timeout=timeout,
                                  ssh_server=ssh_server,
                                  ssh_keyfile=ssh_keyfile)
        else:
            client = self.client

        try:
            if isinstance(msg, list):
                for i, command in enumerate(msg):
                    clm = self._console(client, command['cmd'], opts,
                                        command['msg'])
                    print("%s: %s" % (i, clm))
            else:
                print(self._console(client, cmd, opts, msg))
        except CallError as e:
            msg = str(e)
            if 'timed out' in str(e).lower():
                msg += TIMEOUT_MSG
            sys.stderr.write(msg)
            return 1
        finally:
            if endpoint is not None:
                client.stop()

        return 0


class CircusCtl(cmd.Cmd, object):
    """CircusCtl tool."""
    prompt = '(circusctl) '

    def __new__(cls, client, commands, *args, **kw):
        """Auto add do and complete methods for all known commands."""
        cls.commands = commands
        cls.controller = ControllerApp(commands, client)
        cls.client = client
        for name, cmd in commands.items():
            cls._add_do_cmd(name, cmd)
            cls._add_complete_cmd(name, cmd)
        return super(CircusCtl, cls).__new__(cls, *args, **kw)

    def __init__(self, client, *args, **kwargs):
        super(CircusCtl, self).__init__()

    @classmethod
    def _add_do_cmd(cls, cmd_name, cmd):
        def inner_do_cmd(cls, line):
            arguments = parse_arguments([cmd_name] + shlex.split(line),
                                        cls.commands)
            cls.controller.run(arguments['args'])
        inner_do_cmd.__doc__ = textwrap.dedent(cmd.__doc__)
        inner_do_cmd.__name__ = "do_%s" % cmd_name
        setattr(cls, inner_do_cmd.__name__, inner_do_cmd)

    @classmethod
    def _add_complete_cmd(cls, cmd_name, cmd):
        def inner_complete_cmd(cls, *args, **kwargs):
            if hasattr(cmd, 'autocomplete'):
                try:
                    return cmd.autocomplete(cls.client, *args, **kwargs)
                except Exception as e:
                    sys.stderr.write(str(e) + "\n")
                    traceback.print_exc(file=sys.stderr)
            else:
                return []
        inner_complete_cmd.__doc__ = "Complete the %s command" % cmd_name
        inner_complete_cmd.__name__ = "complete_%s" % cmd_name
        setattr(cls, inner_complete_cmd.__name__, inner_complete_cmd)

    def do_EOF(self, line):
        return True

    def postloop(self):
        sys.stdout.write('\n')

    def autocomplete(self, autocomplete=False, words=None, cword=None):
        """
        Output completion suggestions for BASH.

        The output of this function is passed to BASH's `COMREPLY` variable and
        treated as completion suggestions. `COMREPLY` expects a space
        separated string as the result.

        The `COMP_WORDS` and `COMP_CWORD` BASH environment variables are used
        to get information about the cli input. Please refer to the BASH
        man-page for more information about this variables.

        Subcommand options are saved as pairs. A pair consists of
        the long option string (e.g. '--exclude') and a boolean
        value indicating if the option requires arguments. When printing to
        stdout, a equal sign is appended to options which require arguments.

        Note: If debugging this function, it is recommended to write the debug
        output in a separate file. Otherwise the debug output will be treated
        and formatted as potential completion suggestions.
        """
        autocomplete = autocomplete or 'AUTO_COMPLETE' in os.environ

        # Don't complete if user hasn't sourced bash_completion file.
        if not autocomplete:
            return

        words = words or os.environ['COMP_WORDS'].split()[1:]
        cword = cword or int(os.environ['COMP_CWORD'])

        try:
            curr = words[cword - 1]
        except IndexError:
            curr = ''

        subcommands = get_commands()

        if cword == 1:  # if completing the command name
            print(' '.join(sorted([x for x in subcommands
                                   if x.startswith(curr)])))
        sys.exit(1)

    def start(self, globalopts):
        self.autocomplete()

        self.controller.globalopts = globalopts

        args = globalopts['args']
        parser = globalopts['parser']

        if hasattr(args, 'command'):
            sys.exit(self.controller.run(globalopts['args']))

        if args.help:
            for command in sorted(self.commands.keys()):
                doc = textwrap.dedent(self.commands[command].__doc__)
                help = doc.split('\n')[0]
                parser.add_argument(command, help=help)
            parser.print_help()
            sys.exit(0)

        # no command, no --help: enter the CLI
        print(VERSION)
        self.do_status('')
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            sys.stdout.write('\n')
        sys.exit(0)


def parse_arguments(args, commands):
    _Help.commands = commands

    options = {
        'endpoint': {'default': None, 'help': 'connection endpoint'},
        'timeout': {'default': 5, 'help': 'connection timeout',
                    'type': int},

        'help': {
            'default': False,
            'action': 'store_true',
            'help': 'Show help and exit'},

        'json': {'default': False, 'action': 'store_true',
                 'help': 'output to JSON'},

        'prettify': {
            'default': False,
            'action': 'store_true',
            'help': 'prettify output'},

        'ssh': {
            'default': None,
            'help': 'SSH Server in the format user@host:port'},

        'ssh_keyfile': {
            'default': None,
            'help': 'the path to the keyfile to authorise the user'},

        'version': {
            'default': False,
            'action': 'version',
            'version': VERSION,
            'help': 'display version and exit'},
    }

    parser = argparse.ArgumentParser(
        description="Controls a Circus daemon",
        formatter_class=_Help, usage=USAGE, add_help=False)

    for option in sorted(options.keys()):
        parser.add_argument('--' + option, **options[option])

    if any([value in commands for value in args]):
        subparsers = parser.add_subparsers(dest='command')

        for command, klass in commands.items():

            subparser = subparsers.add_parser(command)
            subparser.add_argument('args', nargs="*",
                                   help=argparse.SUPPRESS)
            for option in klass.options:
                __, name, default, desc = option
                if isinstance(default, bool):
                    action = 'store_true'
                else:
                    action = 'store'

                subparser.add_argument('--' + name, action=action,
                                       default=default, help=desc)

    args = parser.parse_args(args)

    globalopts = {'args': args, 'parser': parser}
    for option in options:
        globalopts[option] = getattr(args, option)
    return globalopts


def main():
    logging.basicConfig()
    # TODO, we should ask the server for its command list
    commands = get_commands()
    globalopts = parse_arguments(sys.argv[1:], commands)
    if globalopts['endpoint'] is None:
        globalopts['endpoint'] = os.environ.get('CIRCUSCTL_ENDPOINT',
                                                DEFAULT_ENDPOINT_DEALER)
    client = CircusClient(endpoint=globalopts['endpoint'],
                          timeout=globalopts['timeout'],
                          ssh_server=globalopts['ssh'],
                          ssh_keyfile=globalopts['ssh_keyfile'])

    CircusCtl(client, commands).start(globalopts)


if __name__ == '__main__':
    main()
