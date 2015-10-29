#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=python
TEST_ARGS="-py $*"

run_test
