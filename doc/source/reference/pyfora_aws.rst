
pyfora_aws
==========

``pyfora_aws`` is a command-line tool that makes it easy to launch and manage :mod:`pyfora` compute clusters
on AWS_. It is installed as part of the :mod:`pyfora` package.


.. note::

    All instances in a cluster run in the same EC2 region, VPC and subnet (if using VPC), and security group.
    If you need to run more than one cluster in a region, use different VPCs, subnets, or security groups.


start
-----

Launches one or more backend instances.
::

    Usage: pyfora_aws start [OPTIONS]

    Optional arguments:
    -h, --help                  show this help message and exit
    -y, --yes-all               Do not prompt user input. Answer "yes" to all prompts.

    --ec2-region EC2_REGION
                                The EC2 region in which instances are launched. Can
                                also be set using the PYFORA_AWS_EC2_REGION
                                environment variable. Default: us-east-1

    --vpc-id VPC_ID
                                The id of the VPC into which instances are launched.
                                EC2 Classic is used if this argument is omitted.

    --subnet-id SUBNET_ID
                                The id of the VPC subnet into which instances are launched.
                                This argument must be specified if --vpc-id is used
                                and is ignored otherwise.

    --security-group-id SECURITY_GROUP_ID
                                The id of the EC2 security group into which instances are launched.
                                If omitted, a security group called "pyfora ssh" (or "pyfora open"
                                if --open-public-port is specified) is created. If a security group
                                with that name already exists, it is used as-is.

    -n NUM_INSTANCES, --num-instances NUM_INSTANCES
                                The number of instances to launch. Default: 1

    --ssh-keyname SSH_KEYNAME
                                The name of the EC2 key-pair to use when launching instances.
                                Can also be set using the PYFORA_AWS_SSH_KEYNAME environment variable.

    --spot-price SPOT_PRICE
                                Launch spot instances with specified max bid price.
                                On-demand instances are launch if this argument is omitted.

    --instance-type INSTANCE_TYPE
                                The EC2 instance type to launch.
                                Default: c3.8xlarge

    --open-public-port
                                If specified, HTTP access to the manager machine will
                                be open from anywhere (0.0.0.0/0). Use with care!
                                Anyone will be able to connect to your cluster. As an
                                alternative, considering tunneling pyfora's HTTP port
                                (30000) over SSH using the -L argument to the `ssh` command.

    --commit COMMIT
                                Run the backend services from a specified commit in the ufora/ufora
                                GitHub repository.


Examples
^^^^^^^^

.. code-block:: bash

    $ pyfora_aws start --vpc-id vpc-0c73f14e --subnet-id subnet-7214f1a0 --ssh-keyname my_key -n 3


This will launch a cluster of three c3.8xlarge instances into the specified VPC and subnet in the default
us-east-1 region, and use the EC2 ssh key-pair called ``my_key``.


.. code-block:: bash

    $ pyfora_aws start --instance-type g2.2xlarge --spot-price 0.3 --open-public-port

This will launch a single g2.2xlarge spot instance with a maximum bid price of $0.3 and open inbound
traffic on port 30000.


add
---

Adds one or more workers to a running cluster.
::

    Usage: pyfora_aws add [OPTIONS]

    optional arguments:
    -h, --help                  show this help message and exit

    --ec2-region EC2_REGION
                                The EC2 region in which instances are launched. Can
                                also be set using the PYFORA_AWS_EC2_REGION
                                environment variable. Default: us-east-1

    --vpc-id VPC_ID             The id of the VPC into which instances are launched.
                                EC2 Classic is used if this argument is omitted.

    --subnet-id SUBNET_ID
                                The id of the VPC subnet into which instances are
                                launched. This argument must be specified if --vpc-id
                                is used and is ignored otherwise.

    --security-group-id SECURITY_GROUP_ID
                                The id of the EC2 security group into which instances
                                are launched.

    -n NUM_INSTANCES, --num-instances NUM_INSTANCES
                                The number of instances to launch. Default: 1

    --spot-price SPOT_PRICE
                                Launch spot instances with specified max bid price.
                                On-demand instances are launch if this argument is
                                omitted.

.. note::

    Instance type is selected automatically based on the type of instances already running.
    It is not possible to mix different types of instances in the same cluster.


Examples
^^^^^^^^

.. code-block:: bash

    $ pyfora_aws add -n 3 --ec2-region us-west-2 --security-group-id sg-2f28a1c0

This adds three instances to an existing cluster running in the ``us-west-2`` region with security
group ``sg-2f28a1c0``.


list
----

Print a list of running backend instances.
::

    usage: pyfora_aws list [OPTIONS]

    optional arguments:
    -h, --help                  show this help message and exit

    --ec2-region EC2_REGION
                                The EC2 region in which instances are launched. Can
                                also be set using the PYFORA_AWS_EC2_REGION
                                environment variable. Default: us-east-1

    --vpc-id VPC_ID             The id of the VPC into which instances are launched.
                                EC2 Classic is used if this argument is omitted.

    --subnet-id SUBNET_ID
                                The id of the VPC subnet into which instances are
                                launched. This argument must be specified if --vpc-id
                                is used and is ignored otherwise.

    --security-group-id SECURITY_GROUP_ID
                                The id of the EC2 security group into which instances
                                are launched. If omitted, a security group called
                                "pyfora ssh" (or "pyfora open" if --open-public-port
                                is specified) is created. If a security group with
                                that name already exists, it is used as-is.

Examples
^^^^^^^^

.. code-block:: bash
   :emphasize-lines: 1

    $ pyfora_aws list --ec2-region us-west-1
    3 instances:
        i-dc7acd1f | 50.18.72.241 | running | worker
        i-387ccbfb | 54.176.35.132 | running | worker
        i-ba7bcc79 | 54.177.18.215 | running | worker

stop
----

Stops all backend instances in the specified region, VPC and subnet, and security-group.
::

    Usage: pyfora_aws stop [OPTIONS]

    optional arguments:
    -h, --help                  show this help message and exit

    --ec2-region EC2_REGION
                                The EC2 region in which instances are launched. Can
                                also be set using the PYFORA_AWS_EC2_REGION
                                environment variable. Default: us-east-1

    --vpc-id VPC_ID             The id of the VPC into which instances are launched.
                                EC2 Classic is used if this argument is omitted.

    --subnet-id SUBNET_ID
                                The id of the VPC subnet into which instances are
                                launched. This argument must be specified if --vpc-id
                                is used and is ignored otherwise.

    --security-group-id SECURITY_GROUP_ID
                                The id of the EC2 security group into which instances
                                are launched. If omitted, a security group called
                                "pyfora ssh" (or "pyfora open" if --open-public-port
                                is specified) is created. If a security group with
                                that name already exists, it is used as-is.

    --terminate                 Terminate running instances. Otherwise, they are just stopped.


Examples
^^^^^^^^

.. code-block:: bash
   :emphasize-lines: 1

    $ pyfora_aws stop --ec2-region us-west-1 --terminate
    Terminating 3 instances:
        i-dc7acd1f | 50.18.72.241 | running | worker
        i-387ccbfb | 54.176.35.132 | running | worker
        i-ba7bcc79 | 54.177.18.215 | running | worker

deploy
------

Deploys a build to all running instances.

.. note::
    This command is typically only used during development of backend services.
    It is rarely used in normal operations.


.. code-block:: none

    Usage: pyfora_aws deploy -i IDENTITY_FILE -p PACKAGE [OPTIONS]

    optional arguments:
    -h, --help                  show this help message and exit

    -i IDENTITY_FILE, --identity-file IDENTITY_FILE
                                The file from which the private SSH key is read.

    -p PACKAGE, --package PACKAGE
                                Path to the backend package to deploy.

    --ec2-region EC2_REGION
                                The EC2 region in which instances are launched. Can
                                also be set using the PYFORA_AWS_EC2_REGION
                                environment variable. Default: us-east-1

    --vpc-id VPC_ID             The id of the VPC into which instances are launched.
                                EC2 Classic is used if this argument is omitted.

    --subnet-id SUBNET_ID
                                The id of the VPC subnet into which instances are
                                launched. This argument must be specified if --vpc-id
                                is used and is ignored otherwise.

    --security-group-id SECURITY_GROUP_ID
                                The id of the EC2 security group into which instances
                                are launched. If omitted, a security group called
                                "pyfora ssh" (or "pyfora open" if --open-public-port
                                is specified) is created. If a security group with
                                that name already exists, it is used as-is.




.. _AWS: https://aws.amazon.com/


