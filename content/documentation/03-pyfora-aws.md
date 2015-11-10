---
layout: main
title: pyfora_aws
tagline: Launch Ufora instances in AWS
category: documentation
---

A command-line utility for launching and managing Ufora workers on AWS.


# Usage

```
usage: pyfora_aws [-h] {start,list,stop} ...

positional arguments:
  {start,list,stop}
    start            Launch ufora instances
    list             List running ufora instances
    stop             Stop all ufora instances

optional arguments:
  -h, --help         show this help message and exit
```


## start

```
usage: pyfora_aws start [-h] [--ec2-region EC2_REGION]
                        [-n NUM_INSTANCES]
                        [--ssh-keyname SSH_KEYNAME]
                        [--spot-price SPOT_PRICE]
                        [--instance-type INSTANCE_TYPE]
                        [--vpc-id VPC_ID]
                        [--subnet-id SUBNET_ID]
                        [--security-group-id SECURITY_GROUP_ID]
                        [--open-public-port]

optional arguments:
  -h, --help            show this help message and exit
  --ec2-region EC2_REGION
                        Required. The EC2 region in which instances
                        are launched.  Can also be set using the
                        PYFORA_AWS_EC2_REGION environment variable.
                        Default: us-east-1
  -n NUM_INSTANCES, --num-instances NUM_INSTANCES
                        The number of instances to launch. Default: 1
  --ssh-keyname SSH_KEYNAME
                        The name of the EC2 key-pair to use when
                        launching instances. Can also be set using the
                        PYFORA_AWS_SSH_KEYNAME environment variable.
  --spot-price SPOT_PRICE
                        Launch spot instances with specified max bid
                        price. On-demand instances are launch if this
                        argument is omitted.
  --instance-type INSTANCE_TYPE
                        The EC2 instance type to launch.
                        Default: c3.8xlarge
  --vpc-id VPC_ID       The id of the VPC to launch instances into.
                        EC2 Classic is used if this argument is
                        omitted.
  --subnet-id SUBNET_ID
                        The id of the VPC subnet to launch instances
                        into. This argument must be specified if
                        --vpc-id is used and is ignored otherwise.
  --security-group-id SECURITY_GROUP_ID
                        The id of the EC2 security group to launch
                        instances into. If omitted, a security group
                        called "ufora" will be created and used.
  --open-public-port    If specified, HTTP access to the manager
                        machine will be open from anywhere.
                        Use with care! Anyone will be able to connect
                        to your cluster.
                        As an alternative, considering
                        tunneling Ufora's HTTP port (30000) over SSH
                        using the -L argument.
```


## list

```
usage: pyfora_aws list [-h] [--ec2-region EC2_REGION]

optional arguments:
  -h, --help            show this help message and exit
  --ec2-region EC2_REGION
                        Required. The EC2 region in which instances
                        are launched. Can also be set using the
                        PYFORA_AWS_EC2_REGION environment variable.
                        Default: us-east-1
```


## stop

```
usage: pyfora_aws stop [-h] [--ec2-region EC2_REGION] [--terminate]

optional arguments:
  -h, --help            show this help message and exit
  --ec2-region EC2_REGION
                        Required. The EC2 region in which instances
                        are launched. Can also be set using the
                        PYFORA_AWS_EC2_REGION environment variable.
                        Default: us-east-1
  --terminate           Terminate running instances.
```
