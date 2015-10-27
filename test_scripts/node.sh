#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

echo
echo "********************************************************************************"
echo "*    EXECUTING node.js tests"
echo "********************************************************************************"
echo
kill_all_running_procs

mocha --reporter spec --compilers coffee:coffee-script/register $WORKSPACE/ufora/web/relay/server/unitTests/* &> $TEST_OUTPUT_DIR/nodejs.log
if [ $? -ne 0 ]; then
	cat $TEST_OUTPUT_DIR/nodejs.log
	exit 1
fi
