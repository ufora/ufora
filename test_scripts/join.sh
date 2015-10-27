#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=join
TEST_ARGS="-py -filter=DataTask"

setup_virtualenv
run_test

