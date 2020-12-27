.PHONY: flake8 dist twine twine-test integration-tests env-test network-test black mypy linting mypy-strict bandit bandit-strict

ifeq ($(OS),Windows_NT)
MOCKSPATH := tests\mocks;
INTEGRATION_CONFIG := tests/monitor-windows.ini
else
MOCKSPATH := $(PWD)/tests/mocks:
INTEGRATION_CONFIG := tests/monitor.ini
endif
PIPENV := $(shell which poetry)

flake8:
	poetry run flake8 *.py simplemonitor/

integration-tests:
	PATH="$(MOCKSPATH)$(PATH)" $(PIPENV) run coverage run monitor.py -1 -v -d -f $(INTEGRATION_CONFIG) -j 1

integration-tests-threaded:
	PATH="$(MOCKSPATH)$(PATH)" $(PIPENV) run coverage run monitor.py -1 -v -d -f $(INTEGRATION_CONFIG)

env-test:
	env TEST_VALUE=myenv poetry run coverage run --append monitor.py -t -f tests/monitor-env.ini

unit-test:
	poetry run coverage run --append -m unittest discover -s tests

network-test:
	rm -f master.log
	rm -f client.log
	poetry run tests/test-network.sh

dist:
	rm -f dist/simplemonitor-*
	poetry run python setup.py sdist bdist_wheel

twine-test:
	poetry run python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

twine:
	poetry run python -m twine upload dist/*

black:
	poetry run black --check --diff *.py simplemonitor/

mypy:
	poetry run mypy *.py simplemonitor/

mypy-strict:
	poetry run mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs --disallow-untyped-decorators *.py simplemonitor/

bandit:
	poetry run bandit -r -ll *.py simplemonitor/

bandit-strict:
	poetry run bandit -r -l *.py simplemonitor/

linting: black flake8 mypy bandit

docker-build:
	docker build -f docker/monitor.Dockerfile .

docker-compose-build:
	docker-compose build
