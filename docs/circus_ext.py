import os
from circus.commands import get_commands

_HEADER = """\
.. _cli:

==================
Command-line tools
==================

circus-top
==========

*circus-top* is a top-like console you can run to watch
live your running Circus system. It will display the CPU and Memory
usage.

Example of output::

    -----------------------------------------------------------------------
    circusd-stats
     PID                 CPU (%)             MEMORY (%)
    14252                 0.8                 0.4
                          0.8 (avg)           0.4 (sum)

    dummy
     PID                 CPU (%)             MEMORY (%)
    14257                 78.6                0.1
    14256                 76.6                0.1
    14258                 74.3                0.1
    14260                 71.4                0.1
    14259                 70.7                0.1
                          74.32 (avg)         0.5 (sum)

    ----------------------------------------------------------------------



*circus-top* is a read-only console. If you want to interact with the system, use
*circusctl*.


circusctl
=========

*circusctl* can be used to run any command listed below. For
example, you can get a list of all the watchers::

    $ circusctl list


*circusctl* is just a zeromq client, and if needed you can
drive programmaticaly the Circus system by writing your
own zmq client.

All messages are Json mappings.

For each command below, we provide a usage example with
circusctl but also the input / output zmq messages.

"""


def generate_commands(app):
    path = os.path.join(app.srcdir, "commands")
    ext = app.config['source_suffix']
    if not os.path.exists(path):
        os.makedirs(path)

    tocname = os.path.join(app.srcdir, "commands%s" % ext)

    with open(tocname, "w") as toc:
        toc.write(_HEADER)
        toc.write("circus-ctl commands\n")
        toc.write("-------------------\n\n")

        commands = get_commands()
        for name, cmd in commands.items():
            toc.write("- **%s**: :doc:`commands/%s`\n" % (name, name))

            # write the command file
            refline = ".. _%s:" % name
            fname = os.path.join(path, "%s%s" % (name, ext))
            with open(fname, "w") as f:
                f.write("\n".join([refline, "\n", cmd.desc, ""]))

        toc.write("\n")
        toc.write(".. toctree::\n")
        toc.write("   :hidden:\n")
        toc.write("   :glob:\n\n")
        toc.write("   commands/*\n")

def setup(app):
    app.connect('builder-inited', generate_commands)
