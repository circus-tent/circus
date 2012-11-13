.PHONY: docs build test coverage build_rpm clean

ifndef VTENV_OPTS
VTENV_OPTS = "--no-site-packages"
endif

bin/python:
	virtualenv $(VTENV_OPTS) .
	bin/python setup.py develop

test: bin/python
	bin/pip install tox
	bin/tox

docs: bin/coverage
	bin/pip install sphinx
	SPHINXBUILD=../bin/sphinx-build $(MAKE) -C docs html $^

coverage: bin/coverage
	bin/nosetests --with-coverage --cover-html --cover-html-dir=html --cover-package=circus

bin/coverage: bin/python
	bin/pip install -r test-requirements.txt --use-mirrors
	bin/pip install nose coverage

build_rpm:
	bin/python setup.py bdist_rpm --requires "python26 python-setuptools pyzmq python26-psutil"

clean:
	rm -rf bin .tox include/ lib/ man/ circus.egg-info/ build/
