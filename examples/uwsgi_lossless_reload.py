__author__ = 'Code Cobblers, Inc.'

# This is an example of how to get lossless reload of WSGI web servers with
# circus and uWSGI. You will, of course, need to specify the web app you
# need for uWSGI to run.
#
# Here is the flow:
# 1. You issue a reload command to the watcher
# 2. The watcher starts a new instance of uWSGI
# 3. The watcher issues SIGQUIT to the old instance, which is intercepted by
#    the before_signal hook
# 4. We send SIGTSTP to the old process to tell uWSGI to stop receiving new
#    connections
# 5. We query the stats from the old process in a loop waiting for the old
#    workers to go to the pause state
# 6. We return True, allowing the SIGQUIT to be issued to the old process

from time import time, sleep
import socket
from json import loads
import signal
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

worker_states = {
    'running': "idle busy cheap".split(" "),
    'paused': "pause".split(" "),
}


def get_uwsgi_stats(name, wid):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock = socket.create_connection(('127.0.0.1', 8090 + wid))
    except Exception as e:
        log.error(
            "Error: Connection refused for {0}} on 127.0.0.1:809{1} - {2}"
            .format(name, wid, e))
    received = sock.recv(100000)
    data = bytes()
    while received:
        data += received
        received = sock.recv(100000)
    if not data:
        log.error(
            "Error: No stats seem available for WID {0} of {1}"
            .format(wid, name))
        return
    return loads(data.decode())


def get_worker_states(name, wid):
    stats = get_uwsgi_stats(name, wid)
    if 'workers' not in stats:
        log.error(
            "Error: No workers found for WID {0} of {1}"
            .format(wid, name))
    workers = stats['workers']
    return [
        worker["status"] if 'status' in worker else None for worker in workers
    ]


def wait_for_workers(name, wid, state, timeout_seconds=60):
    timeout = time() + timeout_seconds
    while not all(worker.lower() in worker_states[state]
                  for worker in get_worker_states(name, wid)):
        if timeout_seconds and time() > timeout:
            raise Exception('timeout')
        sleep(0.25)


def extended_stats(watcher, arbiter, hook_name, pid, stats, **kwargs):
    name = watcher.name
    wid = watcher.processes[pid].wid
    uwsgi_stats = get_uwsgi_stats(name, wid)
    for k in ('load', 'version'):
        if k in uwsgi_stats:
            stats[k] = uwsgi_stats[k]
    if 'children' in stats and 'workers' in uwsgi_stats:
        workers = dict((worker['pid'], worker) for worker in uwsgi_stats['workers'])
        for worker in stats['children']:
            uwsgi_worker = workers.get(worker['pid'])
            if uwsgi_worker:
                for k in ('exceptions', 'harakiri_count', 'requests', 'respawn_count', 'status', 'tx'):
                    if k in uwsgi_worker:
                        worker[k] = uwsgi_worker[k]
    return True


def uwsgi_clean_stop(watcher, arbiter, hook_name, pid, signum, **kwargs):
    if len(watcher.processes) > 1 and signum == signal.SIGQUIT:
        wid = watcher.processes[pid].wid
        name = watcher.name
        log.info('{0} pausing'.format(name))
        watcher.send_signal(pid, signal.SIGTSTP)
        try:
            wait_for_workers(name, wid, 'paused')
            log.info('{0} workers idle'.format(name))
        except Exception as e:
            log.error('trouble pausing {0}: {1}'.format(name, e))
    return True
