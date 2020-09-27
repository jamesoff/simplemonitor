.PHONY: flake8 dist twine twine-test integration-tests env-test network-test black mypy linting mypy-strict bandit bandit-strict

ifeq ($(OS),Windows_NT)
ENVPATH := $(shell python -c "import os.path; import sys; print(os.path.join(sys.exec_prefix, 'Scripts'))")\\
MOCKSPATH := tests\mocks;
INTEGRATION_CONFIG := tests/monitor-windows.ini
else
ENVPATH := $(shell pipenv --venv)/bin/
MOCKSPATH := $(PWD)/tests/mocks:
INTEGRATION_CONFIG := tests/monitor.ini
endif
PIPENV := $(shell which pipenv)

flake8:
	pipenv run flake8 *.py simplemonitor/

integration-tests:
	PATH="$(MOCKSPATH)$(PATH)" $(PIPENV) run coverage run monitor.py -1 -v -d -f $(INTEGRATION_CONFIG)

env-test:
	env TEST_VALUE=myenv pipenv run coverage run --append monitor.py -t -f tests/monitor-env.ini

unit-test:
	pipenv run coverage run --append -m unittest discover -s tests

network-test:
	rm -f master.log
	rm -f client.log
	pipenv run tests/test-network.sh

dist:
	rm -f dist/simplemonitor-*
	pipenv run python setup.py sdist bdist_wheel

twine-test:
	pipenv run python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

twine:
	pipenv run python -m twine upload dist/*

black:
	pipenv run black --check --diff *.py simplemonitor/

mypy:
	pipenv run mypy *.py simplemonitor/

mypy-strict:
	pipenv run mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs --disallow-untyped-decorators *.py simplemonitor/

bandit:
	pipenv run bandit -r -ll *.py simplemonitor/

bandit-strict:
	pipenv run bandit -r -l *.py simplemonitor/

linting: black flake8 mypy bandit

docker-build:
	docker build -f docker/monitor.Dockerfile .

docker-compose-build:
	docker-compose build
