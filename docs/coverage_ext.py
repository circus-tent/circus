import os
import coverage
from nose.core import TestProgram
import sys
import StringIO


page = """
Code coverage
=============


::

%s

"""


def generate_coverage(app):
    cov = coverage.coverage()
    cov.start()

    try:
        old_arg = sys.argv[:]
        sys.argv = [sys.executable, 'circus']
        try:
            testprogram = TestProgram(module='circus', exit=False)
        finally:
            sys.argv[:] = old_arg
    finally:
        cov.stop()

    res = StringIO.StringIO()

    target = os.path.join(app.srcdir, 'coverage.rst')
    cov.save()
    cov.report(file=res)
    res.seek(0)

    with open(target, 'w') as f:
        f.write(page % ''.join(["    " + line for line in res.readlines()]))


def setup(app):
    app.connect('builder-inited', generate_coverage)
