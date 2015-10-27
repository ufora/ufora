#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	export WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=scripts
TEST_ARGS="-scripts $*"

run_test

