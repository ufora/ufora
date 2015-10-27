# Installation
This document describes the installation steps for an on-premise Ufora cluster.

## Summary

### Cluster manager installation

1. Create a new directory for the installation:

        $ mkdir ~/ufora

2. Copy the ufora installation package into the new directory.

        $ cp ~/Downloads/ufora-<version>.tar.gz ~/ufora/

3. Go to the installation directory and extract the installation package:

        $ cd ~/ufora
        $ tar xf ufora-<version>.tar.gz

4. Install the cluster manager:

        $ ufora-<version>/install-manager -d ~/ufora

5. Start the server:

        $ bin/start

6. Add a new user to the system:

        $ bin/ufora-shell bin/addUser.py
        Email address: address@org.com
        Password:
        Password (repeat):
        First Name: John
        Last Name: Doe

7. Start a web browser and navigate to https://<manager-address>:30005/


### Worker installation

Follow steps 1-3 from the cluster manager installation. Then:

1. Install the ufora worker:

        $ ufora-<version>/install-worker -d ~/ufora -c <manager-address>

2. Start the ufora worker:

        $ bin/ufora-worker start



## Cluster Topology

A ufora cluster consists of one cluster manager and one or more workers.
NOTE: All workers must run on machines with the same number of CPU cores and the same amount of RAM! The machine running the cluster manager can also run a worker but in that case, it too must have the same number of cores and the same amount of RAM.
Workers join the cluster by connecting to the cluster manager and making their cores availables to users.
When a user requests a certain number of cores, the cluster manager assigns the appropriate number of workers to the user,
effectively creating a small grid dedicated to the owning user.
All computations submitted by the owner are automatically distributed among the assigned workers.
Clients connect to the cluster from their browser by navigating to the cluster manager's HTTPS endpoint, which hosts the Ufora web appliation.


## Prerequisites
* You must be running a supported 64-bit linux distribution. Currently supported versions are:
Ubuntu 12.04 LTS (Precise) or higher, Debian Wheezy or higher, Red Hat Enterprise Linux 6.4 or higher.

* The worker machines must be able to communicate with each other and with the cluster manager.

* The client machine needs to be able to connect to the cluster manager over TCP port 30005. The system can be configured to use a different port.

* The client machine needs an HTML5-compliant web browser.
**Note**: Ufora is fully supported on Google Chrome version 27 or higher. It is known to work on Firefox version 24 or higher, Safari 6.1.1 or higher, and IE 9 or higher but is not thoroughly tested in those environments.


## Ufora Packages
Ufora packages are delivered as tarball files with the naming scheme: ufora-<version>.tar.gz (e.g. ufora-0.7.1.tar.gz).

The package expands to a directory named ufora-<version> that contains the following files:

+ **install-manager.sh**: installs the Ufora cluster manager. A Ufora cluster MUST have exactly one cluster manager
+ **install-worker.sh**:  installs a Ufora worker
+ **README.md**:          release notes
+ **INSTALL.md**:         these instructions


## Installation Steps

The following steps assume that the Ufora package has been copied to ~/ufora/ and extracted there.

After extracting the package your directory structure should look like this:

~/ufora/
+-- ufora-<version>.tar.gz
+-- ufora-<version>/
+------ install-manager.sh
+------ install-worker.sh
+------ INSTALL.md
+------ README.md
+------ lib/

**Note:** The installation scripts create new directories next to the package root directory (e.g. ~/ufora/bin). It is therefore recommended that the package be placed in its own directory (i.e. ~/ufora/) rather than than the root or home directory.


### Cluster Manager
On the machine designated to run the cluster manager:

    $ cd ~/ufora
    $ ufora-<version>/install-manager.sh
    $ bin/start

### Ufora Worker
Workers need to be able to connect to the cluster manager. Before installing workers, make sure you have the cluster manager's IP address available.

    $ cd ~/ufora
    $ ufora-<version>/install-manager.sh <manager_ip_address>
    $ bin/ufora-worker start

### User Accounts
User accounts are created on the cluster manager machine.

    $ cd ~/ufora
    $ bin/ufora-shell bin/addUser.py
    Email address: address@org.com
    Password:
    Password (repeat):
    First Name: John
    Last Name: Doe

You will be prompted for email address, password, first name, and last name.
All fields are required and cannot be left blank.


### Log In
Open your browser and navigate to: https://<manager-ip-address>:30005/

### Demo Projects
The Ufora package includes several demo projects that are available to all users.
Once logged in to the ufora application, click "PROJECTS" on the top navigation-bar, and select the "DEMOS" tab. Click on any of the listed demo projects to open it.
NOTE: Demo projects are shared between all users and are therefore read-only. To play with the code and make changes, click the "Duplicate" link in the project view on the left. This will create a copy of the demo in the current user's account.


## Starting and Stopping Services
Start and stop scripts are installed into the ./bin direcory under the package root (~/ufora/ in the examples above).

### Ufora Worker
To start the ufora worker:

    $ cd ~/ufora
    $ bin/ufora-worker start

To stop the ufora worker:

    $ cd ~/ufora
    $ bin/ufora-worker start

### Cluster Manager
To start the ufora cluster manager:

    $ cd ~/ufora
    $ bin/start

To stop the ufora cluster manager:

    $ cd ~/ufora
    $ bin/stop

The cluster manager consists of several services that can be started and stopped separately. Under normal conditions this should not be necessary but it can be useful when troubleshooting.

#### ufora-store
An in-memory key-value store used to hold persistent data such as fora projects and core assignments.

#### ufora-cluster
The service responsible for maintaining up-to-date view of available workers and assigning them to fulfill user requests.

#### ufora-backend
The service responsible for submitting computations to workers and tracking their status.

#### ufora-web
A node.js web application that handles logins and serves the Ufora graphical interface.


## Installing Updates
Upgrading to a new version of Ufora is similar to a first-time installation.

1. Stop all Ufora workers.
2. Stop the cluster manager.
3. Copy the new package into the ~/ufora directory (e.g. ~/ufora/ufora-<new-version>.tar.gz).
4. Extract the tarball:

        $ cd ~/ufora
        $ tar xvfz ufora-<new-version>.wheezy.tar.gz

5. On the cluster manager:

        $ cd ~/ufora
        $ ufora-<new-version>/install-manager.sh -d ~/ufora
        $ bin/start

6. On the workers:

        $ cd ~/ufora
        $ ufora-<new-version>/install-worker.sh -d ~/ufora -c <cluster_manager_address>
        $ bin/ufora-worker start

7. At this point the new version of ufora is running and the old package can be safely deleted.

