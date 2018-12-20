#!/usr/bin/env bash

set -exu

run_test() {
	server_config=$1
	client_config=$2

	echo "==> Running network test with server config $server_config and client config $client_config"

	rm -f network.log

	# start the master instance
	COVERAGE_FILE=.coverage.1 coverage run --debug=dataio monitor.py -f "tests/network/master/$server_config" -d --loops=2 &
	sleep 1

	# run the client instance
	COVERAGE_FILE=.coverage.2 coverage run --debug=dataio monitor.py -f "tests/network/client/$client_config" -1 -d

	# let them run
	sleep 15

	# make sure the client reached the master
	grep test2 network.log
	grep test3 network.log

	wait

	coverage combine --append

	echo "==> Completed network test"
	echo
}

run_test monitor.ini monitor.ini
run_test monitor-no-pickle.ini monitor.ini
run_test monitor.ini monitor-ipv6.ini
