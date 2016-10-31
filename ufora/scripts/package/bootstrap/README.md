# Bootstrapping Ufora With fakechroot

## Overview

This guide describes a process for creating a clean distribution of Debian Wheezy or Ubuntu Precise in a local directory, installing Ufora into it, and running it using fakechroot.

Once the few bootstrapping dependencies are installed, the entire process runs as an unprivileged user and does not require root permissions.

It uses *debootstrap* to initialize the target directory and then installs required packages using *apt-get* running under fakechroot.

The workflow consists of three shell scripts:

- **bootstrap.sh** - Creates an isolated environment and installs all of Ufora's dependencies into it.
- **install.sh** - Installs a ufora package into an environment created with bootstrap.sh.
- **run.sh** - Launches the installed ufora services and enters a shell in their fakechroot environment.


## Prerequisites

The boostrapping process depends on a handful of packages:
*debootstrap*, *gcc*, *g++*, *git*, *dchroot*, *fakeroot*, *dh-autoreconf*

They can ben installed by running:

	sudo apt-get install -y debootstrap gcc g++ git dchroot fakeroot dh-autoreconf


## Installation
First create a directory to be used as the bootstrapping target. In this example we use *~/ufora*.

		$ mkdir ~/ufora


### bootstrap.sh

Creates an isolated environment in a specified directory and installs all of Ufora's dependencies into it.

**Synopsis:**

	bootstrap.sh -r <precise|wheezy> -d <target_dir> [-s]
		
	Options:
	    -r <precise|wheezy>   the Debian/Ubuntu release to use for bootstraping. Can be one of 'precise, wheezy'.
	    -d <target_dir>       the root directory under which everything is installed.

	    -s                    call fakechroot with --use-system-libs


To bootstrap a Debian Wheezy image, run:
		
	$ ./bootstrap.sh -r wheezy -d ~/ufora
	
This will take several minutes to complete. It creates the directory *~/ufora/image* as the root of the new file-system.

It may also download and build *fakechroot* from source if the system's version is older than 2.17.3.


### install.sh

Installs ufora services from a specified ufora package into a target directory created with bootstrap.sh.

**Synopsis:**

	install.sh (worker -m <manager_address> | manager) -d <target_dir> -u <ufora_package> [-s]

	Options:
    	-d <target_dir>       the root directory under which everything is installed.
	    -u <ufora_package>    path to a tarball containing a ufora distribution.
    	-m <manager_address>  IP address or hostname of the cluster manager. Only used with 'worker' command.

	    -s                    call fakechroot with --use-system-libs
	    

To install the Ufora cluster manager from Ufora package *~/ufora-0.7.6.wheezy.tar.gz* run:

	$ ./install.sh manager -d ~/ufora -u ~/ufora-0.7.6.wheezy.tar.gz
	
To install a Ufora worker in a network where the cluster manages run in 192.168.1.85 run:

	$ ./install.sh worker -m 192.168.1.85 -d ~/ufora -u ~/ufora-0.7.6.wheezy.tar.gz
	

### run.sh

Launches the ufora services installed in the specified target directory, and enters a shell in their fakechroot environment.

**Synopsis:**

		run.sh -d <target_dir> [-q] [-s]
		
		Options:
    	-d <target_dir>       the root directory under which everything is installed.
    	-q					   quit all ufora services.

	    -s                    call fakechroot with --use-system-libs
	    

**Note:** This script DOES NOT exit when the ufora services start. It starts a shell session in the fakechroot environment from which the services were started.

### Stopping the Services

**From the fakechroot shell:**

To stop a worker, run:

	$ ~/ufora/bin/ufora-worker stop
	
To stop the cluster manager, run:

	$ ~/ufora/bin/stop

**Forcefully from the host:**

This sends SIGKILL to all ufora services.

	$ ./run -d ~/ufora -q