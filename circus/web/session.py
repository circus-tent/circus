from bottle import request
from circus.web.controller import LiveClient

_CLIENT = None


def get_client():
    return _CLIENT


def set_client(client):
    global _CLIENT
    _CLIENT = client


def get_session():
    environ = getattr(request, 'environ', None)
    if environ is None:
        return None
    return request.environ.get('beaker.session')


def disconnect_from_circus():
    client = get_client()

    if client is not None:
        client.stop()
        set_client(None)
        session = get_session()
        if session is not None:
            session.pop('endpoint')
            session.save()
        return True
    return False


def connect_to_circus(endpoint, ssh_server=None):
    client = LiveClient(endpoint=endpoint, ssh_server=ssh_server)
    client.update_watchers()
    set_client(client)
    session = get_session()
    if session is not None:
        session['endpoint'] = endpoint
        session.save()
    return client
