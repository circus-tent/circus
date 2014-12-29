.. _addingcmds:

Adding new commands
###################

We tried to make adding new commands as simple as possible.

You need to do three things:

1. create a ``your_command.py`` file under ``circus/commands/``.
2. Implement a single class in there, with predefined methods
3. Add the new command in ``circus/commands/__init__.py``.

Let's say we want to add a command which returns the number of watchers
currently in use, we would do something like this (extensively commented to
allow you to follow more easily):

.. code-block:: python

    from circus.commands.base import Command
    from circus.exc import ArgumentError, MessageError
    class NumWatchers(Command):
        """It is a good practice to describe what the class does here.

        Have a look at other commands to see how we are used to format
        this text. It will be automatically included in the documentation,
        so don't be affraid of being exhaustive, that's what it is made
        for.
        """
        # all the commands inherit from `circus.commands.base.Command`

        # you need to specify a name so we find back the command somehow
        name = "numwatchers"

        # Set waiting to True or False to define your default behavior
        # - If waiting is True, the command is run synchronously, and the client may get
        #   back results.
        # - If waiting is False, the command is run asynchronously on the server and the client immediately
        #   gets back an 'ok' response
        #
        #   By default, commands are set to waiting = False
        waiting = True

        # options
        options = [('', 'optname', default_value, 'description')]

        properties = ['foo', 'bar']
        # properties list the command arguments that are mandatory. If they are
        # not provided, then an error will be thrown

        def execute(self, arbiter, props):
            # the execute method is the core of the command: put here all the
            # logic of the command and return a dict containing the values you
            # want to return, if any
            return {"numwatchers": arbiter.numwatchers()}

        def console_msg(self, msg):
            # msg is what is returned by the execute method.
            # this method is used to format the response for a console (it is
            # used for instance by circusctl to print its messages)
            return "a string that will be displayed"
        
        def message(self, *args, **opts):
            # message handles console input.
            # this method is used to map console arguments to the command
            # options. (its is used for instance when calling the command via
            # circusctl)
            # NotImplementedError will be thrown if the function is missing
            numArgs = 1
            if not len(args) == numArgs:
                raise ArgumentError('Invalid number of arguments.')
            else:
                opts['optname'] = args[0]
            return self.make_message(**opts)

        def validate(self, props):
            # this method is used to validate that the arguments passed to the
            # command are correct. An ArgumentError should be thrown in case
            # there is an error in the passed arguments (for instance if they
            # do not match together.
            # In case there is a problem wrt their content, a MessageError
            # should be thrown. This method can modify the content of the props
            # dict, it will be passed to execute afterwards.
