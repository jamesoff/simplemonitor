#!/usr/bin/env bash

set -x

if [[ $TRAVIS_PYTHON_VERSION = 2.6* ]]; then
	pip install unittest2
	mv tests/tests.py .
	sed -i -e 's/import unittest/import unittest2 as unittest/' tests.py
	unit2 discover
else
	python -m unittest discover -s tests
fi
