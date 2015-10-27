#!/bin/bash

# Updates the cluster manager address in the configuration file of 
# a Ufora Worker instance.

if [ -z "$1" ]; then
    echo "Usage: configure_worker.sh <cluster_manager_address>"
    exit 1
fi

SELF_DIR=$(cd $(dirname "$0"); pwd)
sed -i s/^UFORA_CLUSTER_HOST=.*//g $SELF_DIR/image/root/ufora/config.cfg
echo "UFORA_CLUSTER_HOST=$1" >> $SELF_DIR/image/root/ufora/config.cfg
