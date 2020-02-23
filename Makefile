.PHONY: flake8 dist twine twine-test

BINPATH := $(shell pipenv --venv)

flake8:
	pipenv run flake8 --ignore=E501,W503,E203 *.py simplemonitor/

integration-tests:
	pipenv run env PATH="$(PWD)/tests/mocks:$(PATH)" "$(BINPATH)/bin/coverage" run monitor.py -1 -v -d -f tests/monitor.ini

dist:
	rm -f dist/simplemonitor-*
	pipenv run python setup.py sdist bdist_wheel

twine-test:
	pipenv run python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

twine:
	pipenv run python -m twine upload dist/*
