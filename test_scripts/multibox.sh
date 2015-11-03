#!/bin/bash
if [ -z "$WORKSPACE" ]; then
    export WORKSPACE=.
fi
. $WORKSPACE/test_scripts/_funcs.sh

TEST_NAME=multibox
TEST_ARGS="-multibox --logging=info -timeout 600 $*"
export UFORA_CONFIG_FILE=$WORKSPACE/test_scripts/multibox/test.config

run_test
