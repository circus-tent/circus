import os
from circus.commands import get_commands


def generate_commands(app):
    path = os.path.join(app.srcdir, "for-ops", "commands")
    ext = app.config['source_suffix']
    if not os.path.exists(path):
        os.makedirs(path)

    tocname = os.path.join(app.srcdir, "for-ops", "commands%s" % ext)

    commands = get_commands()
    items = commands.items()
    items = sorted(items)

    with open(tocname, "w") as toc:
        toc.write(".. include:: commands-intro%s\n\n" % ext)
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
