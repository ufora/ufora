# HDFS on Marathon

## Overview
This package contains a json configuration file and a corresponding shell script that enable the
deployment of Hadoop HDFS clusters on top of Apache Mesosphere Marathon (https://mesosphere.github.io/marathon/).

## Prerequisites
1. A Mesos cluster with the Marathon framework installed and at least 2 slaves, preferably 4 or more.
2. The Java runtime (JRE) or development kit (JDK) version 7 is installed on all slaves.

## Package Content
The pacakge contains the following files:

1. README.md - these instructions
2. hdfs.json - a template for creating your marathon app configuration. The templates has placeholders for values
you need to provide for your own environment.
3. hdfs-example.json - a sample configuration file.
4. run-hdfs.sh - a bash script that is copied to slaves as part of the Marathon app and is responsible for configuring 
and launching the HDFS name node and data nodes.

## Configuration - hdfs.json
This is the Marathon configuration file that describes the structure, configuration, and dependencies of an HDFS cluster running in Marathon.
It define a single application group (https://mesosphere.github.io/marathon/docs/application-groups.html) called `hadoop`,
which contains an inner group called `hdfs` with two apps: `name-node`, and `data-node`.
If you deploy HDFS as part of a broader application deployment, either of additional hadoop services, or independent applications that require HDFS as a durable store, you may want to introduce additional group(s) for your application components and declare their dependency on HDFS.

In addition to standard Marathon settings like `cpus`, `mem`, and `instances`, there are a few elements you need to configure in order to adapt to your own runtime environment.

### env
The `env` section defines a set of environment variables that are available to the application at runtime:

1. JAVA_HOME: this should point to the JDK or JRE directory on your mesos slaves.
If you run on Ubuntu/Debian and use the openJDK, this path will look something like `/usr/lib/jvm/java-7-openjdk-amd64`.
2. HADOOP_NAMENODE_DIR|HADOOP_DATANODE_DIR: a local directory for the HDFS NameNode/DataNode to keep its data files.
3. HADOOP_NAMENODE_LOG|HADOOP_DATANODE_LOG: a path to a local log file for the HDFS NameNode/DataNode.
4. NAME_NODE_MARATHON_URL: an HTTP url to the Marathon REST API endpoint describing the name-node application.
This is used during data-node installation to determine the hostname and port of the name-node.
5. HADOOP_PREFIX: Relative path to the extracted hadoop package. You do not need to modify this variable unless you switch to a different version of hadoop.
5. HADOOP_CONF_DIR: Local directory for hadoop configuration files. If this is a relative path, it is taken to be relative to $HADOOP_PREFIX.

### uris
This is an array of URIs of files that Marathon copies to the application runtime directory during deployment.
There are two files that need to be present:
1. hadoop-2.7.1.tar.gz - the binary package of Apache Hadoop, available at [http://www.apache.org/dyn/closer.cgi/hadoop/common/hadoop-2.7.1/hadoop-2.7.1.tar.gz]
2. run-hdfs.sh - the bash script included in this package.

URIs can be:
* `http(s)` URLs (e.g. http://www.apache.org/dyn/closer.cgi/hadoop/common/hadoop-2.7.1/hadoop-2.7.1.tar.gz)
* `file` URIs (e.g. file:///home/user/run-hdfs.sh)
* `ftp(s)` URIs
* `hdfs` URIs
* `s3` URIs


## Deployment
Once hdfs.json has been edited for your environment and the necessary files (`hadoop-2.7.1.tar.gz`, and `run-hdfs.sh`) have been made available by copying them to a local or remote directory accesible to the slaves, you can deploy the application group from the terminal.

If you extracted this package to `~/marathon-hdfs`:

1. `cd ~/marathon-hdfs`
2. `curl -i -X POST http://<marathon_server>:<marathon_http_port>/v2/groups -H "Content-Type: application/json" --data-binary "@hdfs.json"`

The response should look something like:

    HTTP/1.1 100 Continue

    HTTP/1.1 201 Created
    X-Marathon-Leader: http://ip-10-253-103-2:8080
    Cache-Control: no-cache, no-store, must-revalidate
    Pragma: no-cache
    Expires: 0
    Location: http://<marathon_server>:<marathon_http_port>/v2/groups/hadoop
    Content-Type: application/json
    Transfer-Encoding: chunked
    Server: Jetty(8.y.z-SNAPSHOT)

    {"version":"2015-08-21T13:55:33.606Z","deploymentId":"14c04fca-740d-4cbb-8c00-8c7d2f79ed52"}


You can now go to the Marathon web console and see the status of your deployment and once the name-node is deployed successfully you can scale the size of the data-node application.

### Accessing the HDFS Web Console
Once the name node is up and running, you can access its web console.
To find out the host and port, go to the Marathon console and click on the `hdfs/name-node` app to go to the App page.
In the App page, you will see the host name of the slave running the name-node (in grey below the green app-id).
Next to the host name are three port numbers in brackets - the HTTP port is the second one.

So if, for example, you see something like:

    ip-10-232-22-163.us-west-2.compute.internal:[31095, 31096, 31097]

You can access the web console by navigating to:

    http://ip-10-232-22-163.us-west-2.compute.internal:31096/


### Uninstalling
To delete an HDFS deployment run the following command:

    curl -i -X DELETE "http://<marathon_server>:<marathon_http_port>/v2/groups/hadoop"

## NOTES

### Security
Hadoop and HDFS support Kerberos security. However, this package DOES NOT configure Kerberos or any other security model.
It runs HDFS unauthenticated.

### HDFS Configuration
If you need to customize internal configuration of HDFS, you may need to edit run-hdfs.sh, which generates the XML configuration files on the name and data nodes.
