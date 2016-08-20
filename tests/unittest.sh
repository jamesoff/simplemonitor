#!/usr/bin/env bash

set -x

if [[ $TRAVIS_PYTHON_VERSION = 2.6* ]]; then
	pip install unittest2
	for f in tests/test_*.py; do
		mv "tests/$f" .
		sed -i -e 's/import unittest/import unittest2 as unittest/' "$f"
	done
	unit2 discover
else
	python -m unittest discover -s tests
fi
