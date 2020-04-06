__author__ = 'Code Cobblers, Inc.'

# This is an example of how to get lossless reload of WSGI web servers with
# circus and uWSGI. You will, of course, need to specify the web app you
# need for uWSGI to run.
#
# This example also solves another problem I have faced many times with uWSGI.
# When you start an app with a defect in uWSGI, uWSGI will keep restarting
# it forever. So this example includes an after_spawn hook that does flapping
# detection on the uWSGI workers.
#
# Here is the flow for a reload:
# 1. You issue a reload command to the watcher
# 2. The watcher starts a new instance of uWSGI
# 3. The after_spawn hook ensures that the workers are not flapping and halts
#    the new process if it is, aborting the reload. This would leave the old
#    process running so that you are not just SOL.
# 4. The watcher issues SIGQUIT to the old instance, which is intercepted by
#    the before_signal hook
# 5. We send SIGTSTP to the old process to tell uWSGI to stop receiving new
#    connections
# 6. We query the stats from the old process in a loop waiting for the old
#    workers to go to the pause state
# 7. We return True, allowing the SIGQUIT to be issued to the old process

from time import time, sleep
import socket
from json import loads
import signal
from circus import logger
import re

worker_states = {
    'running': "idle busy cheap".split(" "),
    'paused': "pause".split(" "),
}
NON_JSON_CHARACTERS = re.compile(r'[\x00-\x1f\x7f-\xff]')


class TimeoutError(Exception):
    """The operation timed out."""


def get_uwsgi_stats(name, wid, base_port):
    sock = socket.create_connection(('127.0.0.1', base_port + wid), timeout=1)
    received = sock.recv(100000)
    data = bytes()
    while received:
        data += received
        received = sock.recv(100000)
    if not data:
        logger.error(
            "Error: No stats seem available for WID %d of %s", wid, name)
        return
    # recent versions of uWSGI had some garbage in the JSON so strip it out
    data = data.decode('latin', 'replace')
    data = NON_JSON_CHARACTERS.sub('', data)
    return loads(data)


def get_worker_states(name, wid, base_port, minimum_age=0.0):
    stats = get_uwsgi_stats(name, wid, base_port)
    if 'workers' not in stats:
        logger.error("Error: No workers found for WID %d of %d", wid, name)
        return ['unknown']
    workers = stats['workers']
    return [
        worker["status"] if 'status' in worker and worker['last_spawn'] < time() - minimum_age else 'unknown'
        for worker in workers
    ]


def wait_for_workers(name, wid, base_port, state, timeout_seconds=60, minimum_age=0):
    started = time()
    while True:
        try:
            if all(worker.lower() in worker_states[state]
                   for worker in get_worker_states(name, wid, base_port, minimum_age)):
                return
        except Exception:
            if time() > started + 3:
                raise
        if timeout_seconds and time() > started + timeout_seconds:
            raise TimeoutError('timeout')
        sleep(0.25)


def extended_stats(watcher, arbiter, hook_name, pid, stats, **kwargs):
    name = watcher.name
    wid = watcher.processes[pid].wid
    try:
        uwsgi_stats = get_uwsgi_stats(name, wid, int(watcher._options.get('stats_base_port', 8090)))
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
    except Exception:
        pass
    return True


def children_started(watcher, arbiter, hook_name, pid, **kwargs):
    name = watcher.name
    wid = watcher.processes[pid].wid
    base_port = int(watcher._options.get('stats_base_port', 8090))
    logger.info('%s waiting for workers', name)
    try:
        wait_for_workers(name, wid, base_port, 'running', timeout_seconds=15,
                         minimum_age=5)
        return True
    except TimeoutError:
        logger.error('%s children are flapping on %d', name, pid)
        return False
    except Exception:
        logger.error('%s not publishing stats on %d', name, pid)
        return False


def clean_stop(watcher, arbiter, hook_name, pid, signum, **kwargs):
    if len(watcher.processes) > watcher.numprocesses and signum == signal.SIGQUIT:
        name = watcher.name
        started = watcher.processes[pid].started
        newer_pids = [p for p, w in watcher.processes.items() if p != pid and w.started > started]
        # if the one being stopped is actually the newer one, just do it
        if len(newer_pids) < watcher.numprocesses:
            return True
        wid = watcher.processes[pid].wid
        base_port = int(watcher._options.get('stats_base_port', 8090))
        logger.info('%s pausing', name)
        try:
            watcher.send_signal(pid, signal.SIGTSTP)
            wait_for_workers(name, wid, base_port, 'paused')
            logger.info('%s workers idle', name)
        except Exception as e:
            logger.error('trouble pausing %s: %s', name, e)
    return True
