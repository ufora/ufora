#!/bin/bash

IFS=':' read -a NAME_NODE_HOST_AND_PORT <<< `curl -sf -H "Accept: text/plain" $NAME_NODE_MARATHON_URL/tasks | head -n2 | tail -n1 | awk '{print $3}'`
NAME_NODE_HOST=${NAME_NODE_HOST_AND_PORT[0]}
NAME_NODE_PORT=${NAME_NODE_HOST_AND_PORT[1]}

ufora-0.8.20/install-worker.sh -d /volumes/ufora -c 10.253.21.224

echo "OBJECT_STORE=hdfs" >> /volumes/ufora/config.cfg
echo "OBJECT_STORE_HDFS_NAME_NODE_HOST=$NAME_NODE_HOST" >> /volumes/ufora/config.cfg
echo "OBJECT_STORE_HDFS_NAME_NODE_PORT=$NAME_NODE_PORT" >> /volumes/ufora/config.cfg

/volumes/ufora/bin/ufora-worker run

