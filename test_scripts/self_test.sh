#!/bin/bash

#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

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
