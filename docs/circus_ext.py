import os

from circus.commands import get_commands



def generate_commands(app):
    path = os.path.join(app.srcdir, "commands")
    ext = app.config['source_suffix']
    if not os.path.exists(path):
        os.makedirs(path)

    tocname = os.path.join(app.srcdir, "commands%s" % ext)

    with open(tocname, "w") as toc:
        toc.write("Circus commands\n")
        toc.write("===============\n\n")

        commands = get_commands()
        for name, cmd in commands.items():
            toc.write("- **%s**: :doc:`commands/%s`\n" % (name, name))

            # write the command file
            refline = ".. _%s:" % name
            fname = os.path.join(path, "%s%s" % (name, ext))
            with open(fname, "w") as f:
                f.write("\n".join([refline, cmd.desc, ""]))

        toc.write(".. toctree::\n")
        toc.write("   :hidden:\n")
        toc.write("   :glob:\n\n")
        toc.write("   commands/*\n")


def setup(app):
    app.connect('builder-inited', generate_commands)
