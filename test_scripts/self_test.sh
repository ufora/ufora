#!/bin/bash

if [ -z "$WORKSPACE" ]; then
	export WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

echo
echo "********************************************************************************"
echo "*    EXECUTING test-harness self-test"
echo "********************************************************************************"
echo
kill_all_running_procs
setup_virtualenv

echo "Verifying that python tests report error correctly"
TEST_HARNESS_TESTS=1 python -u $WORKSPACE/test.py $PYTHON_TEST_ARGS -py -filter=TestHarnessCorrectnessTest &> $WORKSPACE/self_test.log
if [ $? -eq 0 ]; then
    echo "ERROR: Test failures were reported as success!"
    cat $WORKSPACE/self_test.log
    exit 1
fi

echo "Verifying that missing script tests result in failure"
python -u $WORKSPACE/test.py $PYTHON_TEST_ARGS -script --scriptPath this/does/not/exist  &>> $WORKSPACE/self_test.log
if [ $? -eq 0 ]; then
    echo "ERROR: Missing test script did not result in an error!"
    cat $WORKSPACE/self_test.log
    exit 1
fi
