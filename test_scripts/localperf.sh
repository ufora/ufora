#!/bin/bash
if [ -z "$WORKSPACE" ]; then
    WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=localperf
TEST_ARGS="-localperf $*"
TEST_TIMEOUT=1200

run_test
