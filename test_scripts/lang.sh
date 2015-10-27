#!/bin/bash
if [ -z "$WORKSPACE" ]; then
    WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=lang
TEST_ARGS="-v --interpreterTraceDumpFile=$TEST_OUTPUT_DIR/interpreterTraces.log -lang $*"

run_test
