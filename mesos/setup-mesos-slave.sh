#!/bin/bash

function usage {
    echo
    echo "USAGE:"
    echo -e "\t$0 hosts_file master_ip"
    echo
    echo -e "\thosts_file - a text file where each line is a host name of a slave to set up."
    echo -e "\tmaster_ip - the internal ip address of the mesos master."
    echo
}

if [ -z $1 ]; then
    echo "ERROR: Missing hosts file"
    usage
    exit 1
fi

if [ -z $2 ]; then
    echo "ERROR: Missing mesos master internal ip address"
    usage
    exit 1
fi

parallel-ssh -i -t0 -h $1 sudo apt-get update
parallel-ssh -i -t0 -h $1 sudo apt-get install -y docker.io
parallel-ssh -i -t0 -h $1 sudo service docker.io stop
parallel-ssh -i -t0 -h $1 sudo mv /var/lib/docker /mnt
parallel-ssh -i -t0 -h $1 sudo ln -s /mnt/docker /var/lib/docker
parallel-ssh -i -t0 -h $1 sudo service docker.io start
parallel-ssh -i -t0 -h $1 sudo docker pull ubuntu:14.04
parallel-ssh -i -t0 -h $1 sudo socker pull ufora/mesos-slave
parallel-ssh -i -t0 -h $1 sudo docker run -d --name DATA -v /mnt/volumes:/volumes ubuntu:14.04
parallel-ssh -i -t0 -h $1 sudo docker run -d --volumes-from DATA --net="host" -e MESOS_LOG_DIR=/volumes/mesos/log -e MESOS_MASTER=zk://$2:2181/master -e MESOS_WORK_DIR=/volumes/mesos/work ufora/mesos-slave
