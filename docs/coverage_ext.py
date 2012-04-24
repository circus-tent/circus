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
    cov = coverage.coverage(omit=['*test*.py', '*docs/*.py'])
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

    import circus
    sourcedir = os.path.dirname(circus.__file__)

    def _clean(line):
        if sourcedir in line:
            return line.replace(sourcedir, 'circus')
        if line.startswith('Name'):
            line = 'Name' + line[len('Name') + len(sourcedir) - len('circus'):]
        elif line.startswith('TOTAL'):
            line = 'TOTAL' + line[len('TOTAL') + len(sourcedir) - len('circus'):]
        elif line.startswith('---'):
            line = line[len(sourcedir) - len('circus'):]
        return line


    with open(target, 'w') as f:
        f.write(page % ''.join(["    " + _clean(line) for line in res.readlines()]))


def setup(app):
    app.connect('builder-inited', generate_coverage)
