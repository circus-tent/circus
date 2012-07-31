import os

from mako.lookup import TemplateLookup
from bottle import request, route as route_, redirect

from circus import logger, __version__
from circus.web.controller import CallError
from circus.web.session import get_session, connect_to_circus, get_client


def set_message(message):
    session = get_session()
    session['message'] = message
    session.save()


def set_error(message):
    return set_message("An error happened: %s" % message)


def run_command(func, message, redirect_url, redirect_on_error=None,
                args=None, kwargs=None):

    func = getattr(get_client(), func)

    if redirect_on_error is None:
        redirect_on_error = redirect_url
    args = args or ()
    kwargs = kwargs or {}

    try:
        logger.debug('Running %r' % func)
        res = func(*args, **kwargs)
        logger.debug('Result : %r' % res)

        if res['status'] != 'ok':
            message = "An error happened: %s" % res['reason']
    except CallError, e:
        message = "An error happened: %s" % e
        redirect_url = redirect_on_error

    if message:
        set_message(message)
    redirect(redirect_url)


CURDIR = os.path.dirname(__file__)
TMPLS = TemplateLookup(directories=[CURDIR])


def render_template(template, **data):
    """Finds the given template and renders it with the given data.

    Also adds some data that can be useful to the template, even if not
    explicitely asked so.

    :param template: the template to render
    :param **data: the kwargs that will be passed when rendering the template
    """
    tmpl = TMPLS.get_template(template)
    client = get_client()

    # send the last message stored in the session in addition, in the "message"
    # attribute.
    server = '%s://%s' % (request.urlparts.scheme, request.urlparts.netloc)

    return tmpl.render(client=client, version=__version__,
                       session=get_session(), SERVER=server, **data)


def route(*args, **kwargs):
    """Replace the default bottle route decorator and redirect to the
    connection page if the client is not defined
    """
    ensure_client = kwargs.get('ensure_client', True)

    def wrapper(func):
        def client_or_redirect(*fargs, **fkwargs):
            if ensure_client:
                client = get_client()
                session = get_session()

                if client is None:
                    session = get_session()
                    if session.get('endpoint', None) is not None:
                        # XXX we need to pass SSH too here
                        connect_to_circus(session['endpoint'])
                    else:
                        return redirect('/connect')

            return func(*fargs, **fkwargs)
        return route_(*args, **kwargs)(client_or_redirect)
    return wrapper
