#!/usr/bin/env bash

set -exu
without_coverage=${WITHOUT_COVERAGE:-0}

if [[ $without_coverage -eq 1 ]]; then
	my_command="python"
else
	my_command="coverage run --debug=dataio"
fi

run_test() {
	server_config=$1
	client_config=$2
	extra_grep=${3:-}

	echo "==> Running network test with server config $server_config and client config $client_config"

	rm -f network.log

	# start the master instance
	( COVERAGE_FILE=.coverage.1 $my_command monitor.py -f "tests/network/master/$server_config" -d --loops=2 2>&1 | tee -a master.log ) &
	sleep 1

	# run the client instance
	COVERAGE_FILE=.coverage.2 $my_command monitor.py -f "tests/network/client/$client_config" -1 -d 2>&1 | tee -a client.log

	# let them run
	sleep 15

	# make sure the client reached the master
	grep test2 network.log
	grep test3 network.log
	if [[ -n $extra_grep ]]; then
		filename=$( echo "$extra_grep" | cut -d= -f1 )
		expr=$( echo "$extra_grep" | cut -d= -f2 )
		grep "$expr" "$filename"
	fi

	wait

	if [[ $without_coverage -ne 1 ]]; then
		coverage combine --append
	fi

	echo "==> Completed network test"
	echo
}

run_test monitor.ini monitor.ini
run_test monitor.ini monitor-ipv6.ini
run_test monitor.ini monitor-id.ini master.log=custom_name
