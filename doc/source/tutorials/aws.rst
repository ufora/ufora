Running pyfora on AWS
======================

If you have an `Amazon Web Services`_ account you can get :mod:`pyfora` running at scale within minutes.
The :mod:`pyfora` package includes an auxiliary script called :doc:`pyfora_aws </reference/pyfora_aws>`, which helps
get you started on AWS.


What You Need to Get Started
----------------------------


AWS Account
^^^^^^^^^^^
You'll need an AWS_ account with an access key that has permission to launch EC2 instances.
If you don't yet have an access key, follow `these instructions`_ to create one.


.. _these instructions: https://aws.amazon.com/developers/access-keys/


boto
^^^^^^

The :doc:`pyfora_aws </reference/pyfora_aws>` tool uses boto_ to communicate with AWS::

    pip install boto


Launch the Backend
------------------

Credentials
^^^^^^^^^^^

:doc:`pyfora_aws </reference/pyfora_aws>` uses boto_ to interact with EC2 on your behalf.
If you already have a `Boto configuration file`_ with your credentials then no additional configuration in needed.
Otherwise, you can set your credentials using the environment variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.

To set the envrionment variables, open a terminal window and type:

.. sourcecode:: bash

        export AWS_ACCESS_KEY_ID=<your aws access key id>
        export AWS_SECRET_ACCESS_KEY=<your aws secret key>


SSH Key-Pair
^^^^^^^^^^^^

While not strictly required, it is strongly recommended that you register an SSH key-pair with EC2
and use it when launching instances. Otherwise, you will not be able to log in to the launched 
instances for diagnostics and troubleshooting.  See `Amazon EC2 Key Pairs`_ for more information.

.. note::
    This tutorial assumes that you **are** providing an SSH key and uses SSH to tunnel traffic to/from
    launched instances. If you do not wish to use an SSH key, or tunnel HTTP traffic over SSH, please the
    the reference documentation for :doc:`pyfora_aws </reference/pyfora_aws>`.


Start a Backend Instance
^^^^^^^^^^^^^^^^^^^^^^^^

You are now ready to start some instances using :doc:`pyfora_aws </reference/pyfora_aws>`.
The following command will launch and configure a single c3.8xlarge on-demand instance in the
us-east-1 region. It takes about 5-6 minutes to complete:

.. code-block:: bash
    :emphasize-lines: 1

        $ pyfora_aws start --ssh-keyname <name_of_your_SSH_keypair>

        Launching manager instance:
        Mon Mar  7 10:24:42 2016 -- i-4aef5b89: pending /
        Done

        Manager instance started:

            i-4aef5b89 | 184.169.200.155 | running | manager

        To tunnel the pyfora HTTP port (30000) over ssh, run the following command:
            ssh -i <ssh_key_file> -L 30000:localhost:30000 ubuntu@184.169.200.155

        Waiting for services:

        Mon Mar  7 10:26:20 2016 -- Instance:i-4aef5b89: installing dependencies -
        Mon Mar  7 10:29:10 2016 -- Instance:i-4aef5b89: installing docker 1.9 -
        Mon Mar  7 10:30:28 2016 -- Instance:i-4aef5b89: pulling docker image -
        Mon Mar  7 10:30:51 2016 -- Instance:i-4aef5b89: launching service -
        Mon Mar  7 10:30:52 2016 -- Instance:i-4aef5b89: ready
        Done

Where ``<name_of_your_SSH_keypair>`` is the name you gave your SSH key-pair in EC2.



SSH Tunnelling
^^^^^^^^^^^^^^

By default, to keep things secure, :doc:`pyfora_aws </reference/pyfora_aws>` keeps all ports on launched instances
inaccessible to incoming connections, with the exception of port 22 for SSH connections.
The easiest secure way to connect to the launched instance from your machine is by tunnelling ``pyfora``'s
HTTP port - 30000 - over SSH. This means that all traffic between your machine and the instance is
secured by SSH.

To establish a tunnel, open a new terminal window (it will need to stay open for the duration of your
session) and run::

        $ ssh -i <ssh_key_file> -L 30000:localhost:30000 ubuntu@<manager_ip_address>

Where ``<ssh_key_file>`` is the path to the private key file of the SSH key-pair you specified when
launching the instance, and ``<manager_ip_address>`` is the public IP address of the manager machine
(184.169.200.155 in the example above).

The ``-L`` option tells SSH to map port ``30000`` on your local machine to ``localhost:30000`` on
the remote.


Connect to the Backend
-------------------------

Now that the SSH tunnel is open you can connect to the backend using ``localhost:30000``.
To verify your connection, copy the code below to a new ``test_pyfora.py`` file::


    import pyfora
    cluster = pyfora.connect('http://localhost:30000')

    with cluster.remotely.downloadAll():
        x = sum(xrange(10**9))

    print x


And run it in your terminal:

.. code-block:: bash
    :emphasize-lines: 1

    $ python test_pyfora.py
    499999999500000000


Adding Instances
----------------

If you need more compute power you can easily increase the size of your cluster by launching additional
instances. The following command add two more c3.8xlarge instances to your running backend:

.. code-block:: bash
    :emphasize-lines: 1

    $ pyfora_aws add -n 2
    Tue Mar  7 10:52:57 2016 -- pending (2) /
    Tue Mar  7 10:53:04 2016 -- running (1), pending (1) \
    Done

    Workers started:
        i-3c9324ff | 54.219.34.156 | running | worker
        i-149225d7 | 54.219.31.180 | running | worker

    Waiting for services:

    Tue Mar  7 10:54:20 2016 -- installing dependencies (2) -
    Tue Mar  7 10:54:37 2016 -- installing dependencies (1), installing docker 1.9 (1) \
    Tue Mar  7 10:57:09 2016 -- installing docker 1.9 (2) \
    Tue Mar  7 10:58:04 2016 -- installing docker 1.9 (1), pulling docker image (1) /
    Tue Mar  7 10:58:37 2016 -- pulling docker image (2) -
    Tue Mar  7 10:58:41 2016 -- launching service (1), pulling docker image (1) /
    Tue Mar  7 11:00:01 2016 -- ready (1), pulling docker image (1) -
    Tue Mar  7 11:00:17 2016 -- ready (1), launching service (1) |
    Tue Mar  7 11:00:18 2016 -- ready (2)
    Done


Stopping Instances
------------------

To terminate all instances in your cluster run:

.. code-block:: bash
    :emphasize-lines: 1

    $ pyfora_aws stop --terminate
    Terminating 3 instances:
        i-3c9324ff | 54.219.34.156 | running | worker
        i-799423ba | 54.176.73.201 | running | manager
        i-149225d7 | 54.219.31.180 | running | worker




.. _Amazon Web Services: https://aws.amazon.com/
.. _AWS: https://aws.amazon.com/
.. _Amazon EC2 Key Pairs: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html

.. _boto: http://boto.cloudhackers.com/en/latest/index.html
.. _Boto configuration file: http://boto.readthedocs.org/en/latest/boto_config_tut.html
