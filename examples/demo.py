import random


def set_var(watcher, arbiter, hook_name):
    watcher.env['myvar'] = str(random.randint(10, 100))
    return True
