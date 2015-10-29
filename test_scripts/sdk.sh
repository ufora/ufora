#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi

. $WORKSPACE/test_scripts/_funcs.sh

echo
echo "********************************************************************************"
echo "*    EXECUTING sdk tests"
echo "********************************************************************************"
echo
kill_all_running_procs

nosetests $WORKSPACE/packages/python &> $WORKSPACE/sdk.log

if [ $? -ne 0 ]; then
	cat $WORKSPACE/sdk.log
	exit 1
fi
