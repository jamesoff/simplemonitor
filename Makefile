.PHONY: flake8 dist twine twine-test integration-tests env-test network-test black mypy linting mypy-strict bandit bandit-strict

ENVPATH := $(shell pipenv --venv)

flake8:
	pipenv run flake8 --ignore=E501,W503,E203 *.py simplemonitor/

integration-tests:
	pipenv run env PATH="$(PWD)/tests/mocks:$(PATH)" "$(ENVPATH)/bin/coverage" run monitor.py -1 -v -d -f tests/monitor.ini

env-test:
	pipenv run env TEST_VALUE=myenv "$(ENVPATH)/bin/coverage" run --append monitor.py -t -f tests/monitor-env.ini

unit-test:
	pipenv run "$(ENVPATH)/bin/coverage" run --append -m unittest discover -s tests

network-test:
	pipenv run tests/test-network.sh

dist:
	rm -f dist/simplemonitor-*
	pipenv run python setup.py sdist bdist_wheel

twine-test:
	pipenv run python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

twine:
	pipenv run python -m twine upload dist/*

black:
	pipenv run "$(ENVPATH)/bin/black" --check --diff *.py simplemonitor/

mypy:
	pipenv run "$(ENVPATH)/bin/mypy" --ignore-missing-imports *.py simplemonitor/

mypy-strict:
	pipenv run "$(ENVPATH)/bin/mypy" --ignore-missing-imports --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs --disallow-untyped-decorators *.py simplemonitor/

bandit:
	pipenv run "$(ENVPATH)/bin/bandit" -r -ll *.py simplemonitor/

bandit-strict:
	pipenv run "$(ENVPATH)/bin/bandit" -r -l *.py simplemonitor/

linting: black flake8 mypy bandit
