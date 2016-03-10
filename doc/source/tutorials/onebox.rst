
Running pyfora on a Single Box
==============================

You can easily run the :mod:`pyfora` backend locally on your machine using docker_.
Then you can connect pyfora to your local backend and start using it to speed up your python code.


What You Need to Get Started
----------------------------

OS
^^
You'll need an OS that can run docker. Currently this means:

* A reasonably recent version of a 64-bit Linux distribution such as:
  Ubuntu, Debian, RedHat, Fedora, Centos, Gentoo, Suse, Amazon, Oracle, etc.
* OS X 10.8 "Mountain Lion" or newer.
* Windows 7.1, 8/8.1 or newer.

.. note::

    Docker only runs *natively* on Linux. On Windows and OS X it runs in a virtual machine.
    As a result, services running in docker containers need to be addressed using the VM's
    IP address instead of ``localhost``. The code examples in this tutorial use ``localhost``
    and should be adjusted when running in non-Linux environments.


Docker
^^^^^^

Docker is available for Linux, OS X, or Windows.
To install docker on your machine, visit http://www.docker.com/, click the Get Started link,
and follow the instructions.

On Linux you can also, optionally, follow `these instructions`_ to enable running docker commands without sudo.
Note, however, that the docker daemon still runs as root - it just saves you five keystrokes when
running docker commands.


.. _docker: https://www.docker.com/
.. _these instructions: http://askubuntu.com/a/477554


Pull the pyfora Service Image
-----------------------------

Once docker is installed you can pull the latest backend service image.

.. code-block:: bash

    $ sudo docker pull ufora/service:latest


.. important::

    If you are not using the most recent pyfora release and don't want to upgrade,
    you will need to use a docker image compatible with your version.
    For example, if you are using pyfora version 0.3.1, you can pull and use the ``ufora/service:0.2``
    image.


Start the Backend Container
---------------------------

The command below starts an all-in-one docker container that runs all the backend services needed to support pyfora.
To run a cluster on multiple machines in a local network, follow the :doc:`instructions here </tutorials/cluster>`.

Create a local directory for the Ufora service logs:

.. code-block:: bash

    $ mkdir ~/ufora

And run (replacing the path ``/home/user`` with your own home directory path):

.. code-block:: bash

    $ sudo docker run -d --name pyfora -p 30000:30000 -v /home/user/ufora:/var/ufora ufora/service

What does this do?
^^^^^^^^^^^^^^^^^^

* ``docker run`` launches a new docker container.
* ``-d`` starts the container as daemon that runs in the background.
* ``--name pyfora`` names the new container pyfora for easy reference in subsequent commands.
* ``-p 30000:30000`` maps port 30000 - pyfora's default HTTP port - to the same port number in your host OS.
  This lets pyfora connect to the container using ``http://localhost:30000``.
* ``-v /home/user/ufora:/var/ufora`` mounts the local directory ~/ufora into /var/ufora within the container.
  This is where Ufora writes all of its log files.
* ``ufora/service`` is the name of the Ufora service image to run. To use a version other than the latest,
  specify a version tag (e.g. ``ufora/service:0.2``).


Verify
------

With your backend container running, you can now verify that ``pyfora`` is able to connect to it.
Open ``python`` in your terminal and run::

    >>> import pyfora
    >>> pyfora.connect('http://localhost:30000')
    <pyfora.Executor.Executor object at 0x7f518a7c1c90>

If no exceptions are thrown, you have a working pyfora cluster running on your machine!

This would be a good point to jump over to the :doc:`/tutorials/intro` tutorial and learn more about
coding with ``pyfora``.


Stopping the pyfora Container
-----------------------------

When you want to stop the pyfora service container, run:

.. code-block:: bash

  $ sudo docker stop pyfora

This stops the container but preserves its state so it can be restarted at a later time.
To permanently delete the container and all its state, run the following command after stopping the container:

.. code-block:: bash

  $ sudo docker rm pyfora


To restart the container after it has been stopped:

.. code-block:: bash

  $ sudo docker start pyfora
