.PHONY: docs

build:
	virtualenv --no-site-packages .
	bin/python setup.py develop
	bin/pip install coverage
	bin/pip install nose

test:
	bin/nosetests -s circus

coverage:
	bin/nosetests --with-coverage --cover-html --cover-html-dir=html --cover-package=circus

docs: html
	$(MAKE) -C docs $^
