#!/bin/bash
if [ -z "$WORKSPACE" ]; then
	export WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=pyfora
TEST_ARGS="-scripts --scriptPath test_scripts/pyfora -timeout 660"

run_test
