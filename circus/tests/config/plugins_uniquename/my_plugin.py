from circus.plugins import CircusPlugin


class MyPlugin(CircusPlugin):

    name = 'my_plugin'

    def __init__(self, *args, **config):
        super(MyPlugin, self).__init__(*args, **config)
        self.name = config.get('name')

    def handle_init(self):
        pass

    def handle_stop(self):
        pass

    def handle_recv(self, data):
        pass
