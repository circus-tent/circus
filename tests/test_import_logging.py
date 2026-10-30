"""Check library logging in fresh interpreters."""
import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize(
    'module', ['circus', 'circus.client', 'circus.watcher'])
def test_import_allows_application_logging_configuration(module):
    code = '''
        import importlib
        import io
        import logging

        root = logging.getLogger()
        assert root.handlers == []
        importlib.import_module({module!r})
        assert root.handlers == []
        assert root.level == logging.WARNING

        output = io.StringIO()
        logging.basicConfig(stream=output, level=logging.DEBUG,
                            format='application: %(message)s')
        logging.getLogger('application').debug('debug message')
        logging.getLogger('circus').info('circus message')
        assert output.getvalue() == ('application: debug message\\n'
                                     'application: circus message\\n')
    '''.format(module=module)
    subprocess.check_call([sys.executable, '-c', textwrap.dedent(code)])


def test_import_preserves_existing_application_handler():
    code = '''
        import io
        import logging

        output = io.StringIO()
        logging.basicConfig(stream=output, level=logging.DEBUG,
                            format='application: %(message)s')
        root = logging.getLogger()
        handlers = list(root.handlers)
        import circus.client
        assert root.handlers == handlers
        assert root.level == logging.DEBUG
        logging.getLogger('application').debug('debug message')
        assert output.getvalue() == 'application: debug message\\n'
    '''
    subprocess.check_call([sys.executable, '-c', textwrap.dedent(code)])


def test_import_leaves_unconfigured_library_logging_quiet():
    code = '''
        import logging
        import circus

        logging.getLogger('circus').warning('unconfigured library warning')
        assert logging.getLogger().handlers == []
    '''
    output = subprocess.check_output(
        [sys.executable, '-c', textwrap.dedent(code)],
        stderr=subprocess.STDOUT)
    assert output == b''
