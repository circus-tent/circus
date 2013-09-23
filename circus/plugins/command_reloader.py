import os

from circus.plugins import CircusPlugin
from circus import logger
from zmq.eventloop import ioloop


class CommandReloader(CircusPlugin):

    name = 'command_reloader'

    def __init__(self, *args, **config):
        super(CommandReloader, self).__init__(*args, **config)
        self.name = config.get('name')
        self.loop_rate = self.config.get('loop_rate', 1) * 1000
        self.cmd_files = {}

    def is_modified(self, watcher, cmd_mtime):
        return (watcher in self.cmd_files
                and cmd_mtime != self.cmd_files[watcher]['mtime'])

    def look_after(self):
        list_ = self.call('list')
        watchers = [watcher for watcher in list_['watchers']
                    if not watcher.startswith('plugin:')]

        for watcher in self.cmd_files.keys():
            if watcher not in watchers:
                del self.cmd_files[watcher]

        for watcher in watchers:
            watcher_info = self.call('get', name=watcher, keys=['cmd'])
            cmd = watcher_info['options']['cmd']
            cmd_path = os.path.realpath(cmd)
            cmd_mtime = os.stat(cmd_path).st_mtime
            if self.is_modified(watcher, cmd_mtime):
                logger.info('%s modified. Restarting.', cmd_path)
                self.call('restart', name=watcher)
            self.cmd_files[watcher] = {
                'filename': cmd_path,
                'mtime': cmd_mtime,
            }

    def handle_init(self):
        self.period = ioloop.PeriodicCallback(self.look_after,
                                              self.loop_rate * 1000,
                                              self.loop)
        self.period.start()
