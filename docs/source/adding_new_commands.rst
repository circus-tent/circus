How to add new commands in circus
#################################

If you want to add a new command, we tried to make this as simple as possible.
You need to do three main things:

1. create a "your_command.py" file under `circus/commands/`.
2. Implement a single class in there, with predefined methods
3. Add the new command in `circus/commands/__init__.py`.

Let's say we want to add a command which returns the number of watchers
actually in use, we would do something like this (extensively commented to
allow you to follow more easily)::

    class NumWatchers(Command):
        """It is a good practice to describe what the class does here.

        Have a look at other commands to see how we are used to format this
        text. It will be used to automatically appear in the documentation of
        circus, so don't be affraid of being exhaustive, that's what it is made
        for.
        """
        # all the commands need to inherit from `circus.commands.base.Command` 

        name = "numwatchers"
        # you need to specify a name so we find back the command somehow

        options = [('', 'optname', default_value, 'description')]
        # XXX describe options

        properties = ['foo', 'bar']
        # properties list the command argments that are mendatory. If they are
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

        def validate(self, props):
            # this method is used to validate that the arguments passed to the
            # command are correct. An ArgumentError should be thrown in case
            # there is an error in the passed arguments (for instance if they
            # do not match together.
            # In case there is a problem wrt their content, a MessageError
            # should be thrown. This method can modify the content of the props
            # dict, it will be passed to execute afterwards.
