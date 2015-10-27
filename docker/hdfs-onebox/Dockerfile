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

