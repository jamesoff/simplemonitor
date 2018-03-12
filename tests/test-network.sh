#!/usr/bin/env bash

set -ex

rm -f network.log

# start the master instance
COVERAGE_FILE=.coverage.1 coverage run --debug=dataio monitor.py -f tests/network/master/monitor.ini -d --loops=2 &
sleep 1

# run the client instance
COVERAGE_FILE=.coverage.2 coverage run --debug=dataio monitor.py -f tests/network/client/monitor.ini -1 -d

# let them run
sleep 15

# make sure the client reached the master 
grep test2 network.log

wait

coverage combine --append
