#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=sort
TEST_ARGS="-py -filter=sort"

setup_virtualenv
run_test
