#!/bin/sh
echo "Current dir: `pwd`"
if [ ! -f ${HDFS_NAMENODE_DIR}/current/VERSION ]; then
    echo Formatting namenode root fs in ${HDFS_NAMENODE_DIR}
    bin/hdfs namenode -format
fi

bin/hdfs namenode &
bin/hdfs datanode
