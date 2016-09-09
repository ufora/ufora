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

FROM ufora/hdfs-base
MAINTAINER Ronen Hilewicz <ronen@ufora.com>

ENV HDFS_NAMENODE_DIR /var/hdfs/namenode
ENV HDFS_DATANODE_DIR /var/hdfs/datanode

VOLUME  ["${HDFS_NAMENODE_DIR}", "${HDFS_DATANODE_DIR}"]

ADD conf/core-site.xml ${HADOOP_CONF_DIR}/core-site.xml
ADD conf/hdfs-site.xml ${HADOOP_CONF_DIR}/hdfs-site.xml
ADD start-hdfs.sh /usr/local/sbin/start-hdfs.sh

EXPOSE 8020 50070 50470 50010 50020 50075 50475

ENTRYPOINT ["/usr/local/sbin/start-hdfs.sh"]

