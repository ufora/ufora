#!/bin/bash

function kill_all_running_procs {
    $WORKSPACE/ufora/scripts/killexp test.py > /dev/null
    $WORKSPACE/ufora/scripts/killexp FakeEC2Machine > /dev/null
    $WORKSPACE/ufora/scripts/killexp nodejs > /dev/null
    $WORKSPACE/ufora/scripts/killexp sharedStateMainline > /dev/null
}

VIRTUALENV_NAME=testenv
function setup_virtualenv {
    rm -rf $WORKSPACE/$VIRTUALENV_NAME > /dev/null

    virtualenv --system-site-packages $VIRTUALENV_NAME
    source $WORKSPACE/$VIRTUALENV_NAME/bin/activate
    pip install -e $WORKSPACE/packages/python --upgrade
    }

function exit_and_cleanup_virtualenv {
    deactivate
    rm -rf $WORKSPACE/$VIRTUALENV_NAME/
}

function run_test {
    echo
    echo "********************************************************************************"
    echo "*    EXECUTING $TEST_NAME tests"
    echo "********************************************************************************"
    echo
    kill_all_running_procs

    TEST_LOG=$TEST_OUTPUT_DIR/$TEST_NAME.log

    if [ -z "$TEST_TIMEOUT" ]; then
        TEST_TIMEOUT=720
    fi

    python -u $WORKSPACE/test.py --baseport=$BASEPORT -timeout=$TEST_TIMEOUT $TEST_ARGS &> $TEST_LOG
    if [ $? -ne 0 ]; then
        cat $TEST_LOG
        exit 1
    fi
}

function stop_tests_and_exit {
    echo
    echo "********************************************************************************"
    echo "*    COLLECTING NOSE RESULTS"
    echo "********************************************************************************"
    echo

    find $WORKSPACE/* -name 'nose*log' | xargs -I {} mv -v '{}' $TEST_OUTPUT_DIR/

    echo
    echo "********************************************************************************"
    echo "*    PACKAGING ARTIFACTS"
    echo "********************************************************************************"
    echo


    find | grep 'core\.[0-9]\+$' | xargs -I{} mv -v '{}' $ARTIFACT_DIR/

    killall -2 redis-cli > /dev/null
    killall redis-server > /dev/null

    tar czf $TEST_OUTPUT_DIR/artifacts.tar.gz $ARTIFACT_DIR/
}

if [ -z $BASEPORT ]; then
    export BASEPORT=30000
fi
export PYTHONPATH=$WORKSPACE

cd $WORKSPACE

if [ -z $NESTED_TESTS_GUARD ]; then
    if [ -z $TEST_OUTPUT_DIR ]; then
        TEST_OUTPUT_DIR=$WORKSPACE
    fi

    export ARTIFACT_DIR=$TEST_OUTPUT_DIR/artifacts
    export ROOT_DATA_DIR=$ARTIFACT_DIR

    echo "ROOT_DATA_DIR: $ROOT_DATA_DIR"

    mkdir $ARTIFACT_DIR

    # Necessary in order to access S3 keys with dots ('.') in their name
    cat > ~/.boto << EOM
[s3]
calling_format = boto.s3.connection.OrdinaryCallingFormat
EOM

    trap stop_tests_and_exit SIGTERM SIGINT SIGHUP SIGPIPE EXIT

    redis-cli MONITOR &> $ARTIFACT_DIR/redis.log &

    echo "Starting redis-server"
    redis-server --dbfilename ufora.rdb --dir $ARTIFACT_DIR --save 60 1 > $ARTIFACT_DIR/redis-server.log &

    export NESTED_TESTS_GUARD=1
fi
