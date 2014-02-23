import os
import sys
from circus.exc import ArgumentError
from circus.commands.base import Command


class IPythonShell(Command):
    """\
       Create shell into circusd process
       =================================

       This command is only useful if you have the ipython package installed.

       Command Line
       ------------

       ::

            $ circusctl ipython

    """

    name = "ipython"

    def message(self, *args, **opts):
        if len(args) > 0:
            raise ArgumentError("Invalid message")
        return self.make_message()

    def execute(self, arbiter, props):
        shell = 'kernel-%d.json' % os.getpid()
        msg = None
        try:
            from IPython.kernel.zmq.kernelapp import IPKernelApp
            if not IPKernelApp.initialized():
                app = IPKernelApp.instance()
                app.initialize([])
                main = app.kernel.shell._orig_sys_modules_main_mod
                if main is not None:
                    sys.modules[
                        app.kernel.shell._orig_sys_modules_main_name
                    ] = main
                app.kernel.user_module = sys.modules[__name__]
                app.kernel.user_ns = {'arbiter': arbiter}
                app.shell.set_completer_frame()
                app.kernel.start()

        except Exception as e:
            shell = False
            msg = str(e)

        return {'shell': shell, 'msg': msg}

    def console_msg(self, msg):
        if msg['status'] == "ok":
            shell = msg['shell']
            if shell:
                from IPython import start_ipython
                start_ipython(['console', '--existing', shell])
                return ''
            else:
                msg['reason'] = 'Could not start ipython kernel'
        return self.console_error(msg)
