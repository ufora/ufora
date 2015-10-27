#!/bin/bash

usage_message="$(basename "$0") -d <data_dir> [-s] [-b <upload_bucket>]

Options:
    -d <data_dir>         Local directory to hold Ufora data files and logs.
    -s                    If included, use real s3; if not, use on-disk s3.
    -b <upload_bucket>    If included, and -s is present, use this S3 bucket
                          for uploads and private datasets. If -s is not present,
                          this argument is ignored.
"
usage() { echo "Usage:"; echo "    $usage_message" 1>&2; exit 1; }

ROOT_DATA_DIR=
USE_REAL_S3=0
USER_DATA_BUCKET=
while getopts "d:b:s" o; do
    case $o in
        d)
            ROOT_DATA_DIR=${OPTARG%%/}
            if [ ! -d "$ROOT_DATA_DIR" ]; then
                echo "ERROR: Data directory '$ROOT_DATA_DIR' does not exist."
                usage
            fi
            ;;

        s)
            USE_REAL_S3=1
            ;;

        b)
            USER_DATA_BUCKET=$OPTARG
            ;;

        *)
            usage
            ;;
    esac
done

if [ -z $ROOT_DATA_DIR ]; then
    echo -e "ERROR: Missing required argument '-d <data_dir>'.\n"
    usage
fi
CONFIG_FILE=$ROOT_DATA_DIR/config.cfg

if [ $USE_REAL_S3 == 0 ]; then
  USER_DATA_BUCKET="ufora.user.data"
fi

SCRIPT_DIR=$(cd $(dirname "$0"); pwd)

if [ -z $UFORA_SERVICE_ACCOUNT ]; then
    UFORA_SERVICE_ACCOUNT=`whoami`
fi

INIT_SCRIPT_PATH=$SCRIPT_DIR/lib/ufora/scripts/init
if [ ! -d $INIT_SCRIPT_PATH ]; then
    INIT_SCRIPT_PATH=$SCRIPT_DIR/../init
fi

. $INIT_SCRIPT_PATH/_config.sh
init_config

# Create data directories (bin, logs, s3_storage, etc.)
# (defined in _config.sh)
create_data_dirs

for service in ufora-store ufora-web ufora-cluster ufora-backend; do
    cp $INIT_SCRIPT_PATH/$service $UFORA_BIN_DIR/
    # use ^ as the sed regex delimiter to avoid escaping forward-slashes.
    sed -i -e "s^<UFORA_CONFIG_FILE>^$CONFIG_FILE^g" $UFORA_BIN_DIR/$service
done

for cert in server.key server.crt ca.crt; do
    if [ ! -f $UFORA_SSL_DIR/$cert ]; then
        cp $UFORA_PACKAGE_ROOT/ufora/machine_model/test_ssl_keys/$cert $UFORA_SSL_DIR/
    fi
done

# Script for adding users to the system
cp $INIT_SCRIPT_PATH/addUser.py $UFORA_BIN_DIR/

# These are convenience scripts for starting and stopping all server components
cp $INIT_SCRIPT_PATH/start $UFORA_BIN_DIR/
cp $INIT_SCRIPT_PATH/stop $UFORA_BIN_DIR/

# A convenience script for starting a one-box cluster simulation.
cp $INIT_SCRIPT_PATH/simulate-cluster $UFORA_BIN_DIR/
sed -i -e "s^<UFORA_PACKAGE_ROOT>^$UFORA_PACKAGE_ROOT^g" $UFORA_BIN_DIR/simulate-cluster

s3Switch=""
if [ $USE_REAL_S3 == 1 ]; then
  s3Switch="-s"
fi

uploadBucketSwitch=""
if [ ! -z $USER_DATA_BUCKET ]; then
  uploadBucketSwitch="-b "$USER_DATA_BUCKET
fi

$SCRIPT_DIR/install-worker.sh -d $ROOT_DATA_DIR $s3Switch $uploadBucketSwitch
