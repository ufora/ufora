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
	WORKSPACE=.
fi

. $WORKSPACE/test_scripts/_funcs.sh

echo
echo "********************************************************************************"
echo "*    EXECUTING sdk tests"
echo "********************************************************************************"
echo
kill_all_running_procs

echo "running git show --shortstat"
echo `git show --shortstat`

nosetests $WORKSPACE/packages/python &> $WORKSPACE/sdk.log

if [ $? -ne 0 ]; then
    echo "got a nonzero exit code (fail)"
    echo "<log output>"
    cat $WORKSPACE/sdk.log
    echo "</log output>"

	cat $WORKSPACE/sdk.log
	exit 1
else
    echo "got a zero exit code (pass)"
    echo "<log output>"
    cat $WORKSPACE/sdk.log
    echo "</log output>"

fi

