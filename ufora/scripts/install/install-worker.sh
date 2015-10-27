#!/bin/bash

usage_message="$(basename "$0") -d <data_dir> -c <cluster_address> [-s] [-b <upload_bucket>]

Options:
    -d <data_dir>         Local directory to hold Ufora data files and logs.
    -c <cluster_address>  Host name or IP address of the cluster manager. 
                          If not passed, defaults to the IP of the current machine.
    -s                    If included, use real s3; if not, use on-disk s3.
    -b <upload_bucket>    If included, and -s is present, use this S3 bucket
                          for uploads and private datasets. If -s is not present,
                          this argument is ignored.
    -m                    Memory limit - maximum amount of RAM (in MB) to be used.
"
usage() { echo "Usage:"; echo "    $usage_message" 1>&2; exit 1; }

ROOT_DATA_DIR=
UFORA_CLUSTER_HOST=
USE_REAL_S3=0
USER_DATA_BUCKET=
while getopts "d:b:c:m:s" o; do
    case $o in
        d)
            ROOT_DATA_DIR=${OPTARG%%/}
            if [ ! -d "$ROOT_DATA_DIR" ]; then
                echo "ERROR: Data directory '$ROOT_DATA_DIR' does not exist."
                usage
            fi
            ;;

        c)
            UFORA_CLUSTER_HOST=$OPTARG
            ;;

        s)
            USE_REAL_S3=1
            ;;

        b)
            USER_DATA_BUCKET=$OPTARG
            ;;

        m)
            if ! [[ $OPTARG =~ ^[0-9]+$ ]]; then
                echo "ERROR: -m argument must be followed by a number."
                usage
            fi
            FORA_MAX_MEM_MB=$OPTARG
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

SCRIPT_DIR=$(cd $(dirname "$0"); pwd)

if [ -z $UFORA_USER ]; then
    UFORA_USER=`whoami`
fi

if [ $USE_REAL_S3 == 0 ]; then
  USER_DATA_BUCKET="ufora.user.data"
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

if [ -f $UFORA_PACKAGE_ROOT/updateAbsolutePaths.sh ]; then
    cd $UFORA_PACKAGE_ROOT
    ./updateAbsolutePaths.sh
else
    echo "Warning: updateAbsolutePaths.sh not found in $UFORA_PACKAGE_ROOT."
fi

for service in ufora-worker ufora-shell; do
    cp $INIT_SCRIPT_PATH/$service $UFORA_BIN_DIR/
    # use ^ as the sed regex delimiter to avoid escaping forward-slashes.
    sed -i -e "s^<UFORA_CONFIG_FILE>^$CONFIG_FILE^g" $UFORA_BIN_DIR/$service
done

