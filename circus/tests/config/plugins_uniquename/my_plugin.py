from circus.tests.test_arbiter import EventLoggingTestPlugin


# Plugin is the same as the EventLoggingTestPlugin,
# just in a directory outside of the circus modules.
class MyPlugin(EventLoggingTestPlugin):
    pass
