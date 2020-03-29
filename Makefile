.PHONY: docs build test coverage build_rpm clean

ifndef VTENV_OPTS
VTENV_OPTS = -p python2.7 --no-site-packages
endif

VENV?=virtualenv

bin/python:
	$(VENV) $(VTENV_OPTS) .
	bin/python setup.py develop

test: bin/python
	bin/pip install tox
	bin/tox

docs:
	bin/pip install -r doc-requirements.txt --use-mirrors
	SPHINXBUILD=../bin/sphinx-build $(MAKE) -C docs html $^

coverage: bin/coverage
	rm -f `pwd`/.coverage
	rm -rf `pwd`/html
	- COVERAGE_PROCESS_START=`pwd`/.coveragerc COVERAGE_FILE=`pwd`/.coverage PYTHONPATH=`pwd` bin/nosetests -s circus/tests
	bin/coverage combine
	bin/coverage html

bin/coverage: bin/python
	bin/pip install -r test-requirements.txt --use-mirrors
	bin/pip install nose coverage

build_rpm:
	bin/python setup.py bdist_rpm --requires "python26 python-setuptools pyzmq python26-psutil"

clean:
	rm -rf bin .tox include/ lib/ man/ circus.egg-info/ build/
	find . -name "*.pyc" | xargs rm -f
	find . -name "*.un~" | xargs rm -f
	find . -name "__pycache__" | xargs rm -rf
