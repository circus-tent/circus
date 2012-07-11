.PHONY: docs build test coverage build_rpm

ifndef VTENV_OPTS
VTENV_OPTS = "--no-site-packages"
endif

build:	
	virtualenv $(VTENV_OPTS) .
	bin/python setup.py develop

test: bin/nosetests
	bin/nosetests -s circus

coverage: bin/coverage
	bin/nosetests --with-coverage --cover-html --cover-html-dir=html --cover-package=circus

docs: bin/sphinx-build
	SPHINXBUILD=../bin/sphinx-build $(MAKE) -C docs html $^

bin/sphinx-build: bin/python
	bin/pip install sphinx
	bin/pip install coverage

bin/nosetests: bin/python
	bin/pip install nose
	bin/pip install WebTest

bin/coverage: bin/python
	bin/pip install coverage

build_rpm:
	bin/python setup.py bdist_rpm --requires "python26 python-setuptools pyzmq python26-psutil"
