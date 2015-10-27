#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=native
TEST_ARGS="-v -native"

run_test
