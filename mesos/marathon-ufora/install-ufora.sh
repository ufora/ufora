#!/bin/bash

#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

IFS=':' read -a NAME_NODE_HOST_AND_PORT <<< `curl -sf -H "Accept: text/plain" $NAME_NODE_MARATHON_URL/tasks | head -n2 | tail -n1 | awk '{print $3}'`
NAME_NODE_HOST=${NAME_NODE_HOST_AND_PORT[0]}
NAME_NODE_PORT=${NAME_NODE_HOST_AND_PORT[1]}

ufora-0.8.20/install-worker.sh -d /volumes/ufora -c 10.253.21.224

echo "OBJECT_STORE=hdfs" >> /volumes/ufora/config.cfg
echo "OBJECT_STORE_HDFS_NAME_NODE_HOST=$NAME_NODE_HOST" >> /volumes/ufora/config.cfg
echo "OBJECT_STORE_HDFS_NAME_NODE_PORT=$NAME_NODE_PORT" >> /volumes/ufora/config.cfg

/volumes/ufora/bin/ufora-worker run

