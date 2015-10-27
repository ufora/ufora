#!/bin/bash

USAGE="Usage: run-hdfs.sh namenode|datanode\n\nInstalls an HDFS name or data node on Marathon"

configure_name_node() {
echo "Name node ports: $PORT0, $PORT1, $PORT2"

cat > $HADOOP_CONF_DIR/hdfs-site.xml << EOM
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file://$HADOOP_NAME_NODE_DIR</value>
        <description>Comma separated list of paths on the local filesystem of a DataNode where it should store its blocks.</description>
    </property>

    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file://$HADOOP_PREFIX/hdfs/namenode</value>
        <description>Path on the local filesystem where the NameNode stores the namespace and transaction logs persistently.</description>
    </property>
    <property>
        <name>dfs.namenode.http-address</name>
        <value>hdfs://`hostname`:$PORT1/</value>
        <description>The address and the base port where the dfs namenode web ui will listen on</description>
    </property>
    <property>
        <name>dfs.namenode.https-address</name>
        <value>hdfs://`hostname`:$PORT2/</value>
        <description>The namenode secure http server address and port</description>
    </property>
    <property>
        <name>dfs.permissions</name>
        <value>false</value>
    </property>
</configuration>
EOM

cat > $HADOOP_CONF_DIR/core-site.xml << EOM
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://`hostname`:$PORT0/</value>
        <description>NameNode URI</description>
    </property>
</configuration>
EOM
}

configure_data_node() {
IFS=':' read -a NAME_NODE_HOST_AND_PORT <<< `curl -sf -H "Accept: text/plain" $NAME_NODE_MARATHON_URL/tasks | head -n1 | awk '{print $3}'`
NAME_NODE_HOST=${NAME_NODE_HOST_AND_PORT[0]}
NAME_NODE_PORT=${NAME_NODE_HOST_AND_PORT[1]}
echo "Name node: $NAME_NODE_HOST:$NAME_NODE_PORT"
echo "Data node ports: $PORT0, $PORT1, $PORT2, $PORT3"

cat > $HADOOP_CONF_DIR/hdfs-site.xml << EOM
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>
    <property>
        <name>dfs.datanode.ipc.address</name>
        <value>`hostname`:$PORT0</value>
        <description>The datanode ipc server address and port</description>
    </property>
    <property>
        <name>dfs.datanode.address</name>
        <value>`hostname`:$PORT1</value>
        <description>The address where the datanode server will listen to</description>
    </property>
    <property>
        <name>dfs.datanode.http.address</name>
        <value>`hostname`:$PORT2</value>
        <description>The datanode http server address and port</description>
    </property>
    <property>
        <name>dfs.datanode.https.address</name>
        <value>`hostname`:$PORT3</value>
        <description>The datanode secure http server address and port</description>
    </property>
    <property>
        <name>dfs.namenode.rpc-address</name>
        <value>$NAME_NODE_HOST:$NAME_NODE_PORT</value>
        <description>NameNode URI</description>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file://$HADOOP_DATANODE_DIR/</value>
        <description>Path on the local filesystem where the DataNode stores data.</description>
    </property>
    <property>
        <name>dfs.permissions</name>
        <value>false</value>
    </property>
</configuration>
EOM

cat > $HADOOP_CONF_DIR/core-site.xml << EOM
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>

<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://$NAME_NODE_HOST:$NAME_NODE_PORT/</value>
        <description>NameNode URI</description>
    </property>
</configuration>
EOM
}

if [[ ! "$HADOOP_PREFIX" = /* ]]; then
    export HADOOP_PREFIX=`pwd`/$HADOOP_PREFIX
fi

if [[ ! "$HADOOP_CONF_DIR" = /* ]]; then
    export HADOOP_CONF_DIR=$HADOOP_PREFIX/$HADOOP_CONF_DIR
fi

if [ -z $1 ]; then
    echo "ERROR: No command specified."
    echo $USAGE
    exit 1
elif [ "$1" = "namenode" ]; then
    configure_name_node

    echo "Formatting name node"
    $HADOOP_PREFIX/bin/hdfs namenode -format -nonInteractive -force

    echo "Starting name node"
    $HADOOP_PREFIX/bin/hdfs namenode
elif [ "$1" == "datanode" ]; then
    configure_data_node
    $HADOOP_PREFIX/bin/hdfs datanode
else
    echo "ERROR: Unrecognized command - $1"
    echo $USAGE
    exit 1
fi
