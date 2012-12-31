import os
from circus.commands import get_commands

_HEADER = """\

.. _commands:

Commands
########

At the epicenter of circus lives the command systems.  *circusctl* is just a
zeromq client, and if needed you can drive programmaticaly the Circus system by
writing your own zmq client.

All messages are Json mappings.

For each command below, we provide a usage example with circusctl but also the
input / output zmq messages.

"""


def generate_commands(app):
    path = os.path.join(app.srcdir, "commands")
    ext = app.config['source_suffix']
    if not os.path.exists(path):
        os.makedirs(path)

    tocname = os.path.join(app.srcdir, "commands%s" % ext)

    commands = get_commands()
    items = commands.items()
    items.sort()

    with open(tocname, "w") as toc:
        toc.write(_HEADER)
        toc.write("circus-ctl commands\n")
        toc.write("-------------------\n\n")

        commands = get_commands()
        for name, cmd in items:
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
