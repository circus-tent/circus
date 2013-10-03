from circus.commands.base import Command


class ReloadConfig(Command):
    """\
        Reload the configuration file
        =============================

        This command reloads the configuration file, so changes in the
        configuration file will be reflected in the configuration of
        circus.


        ZMQ Message
        -----------

        ::

            {
                "command": "reloadconfig",
            }

        The response return the status "ok". If the property graceful is
        set to true the processes will be exited gracefully.


        Command line
        ------------

        ::

            $ circusctl reloadconfig

    """
    name = "reloadconfig"

    def message(self, *args, **opts):
        return self.make_message()

    def execute(self, arbiter, props):
        return arbiter.reload_from_config()
