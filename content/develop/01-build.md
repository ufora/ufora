---
layout: main
title: Build
tagline: How to Build the Ufora Repository
category: develop
---


# Requirements
Ufora development is done on 64-bit Ubuntu 14.04. However, to simplify development on other 
operating systems, a docker image is available with all the necessary build-related packages and dependencies.

All that is required is a 64-bit OS capable of running docker.


# Install Docker

Go to <a href="https://www.docker.com" target="_blank">docker.com</a> and click "Get Started" to download and
install docker.

On Ubuntu 14.04 it's as simple as running:

```bash
$ sudo apt-get update
$ sudo apt-get install docker.io
```

Then to enable command-line TAB completion either restart your shell or run:

```bash
$ source /etc/bash_completion.d/docker.io
```

You can optionally follow [these instructions](http://askubuntu.com/questions/477551/how-can-i-use-docker-without-sudo)
to be able to run docker without `sudo`. Note that it still runs the docker daemon as root -
it just saves you five keystrokes when running docker commands.

Before proceeding you must make sure the docker deamon is started.


# Pull Ufora Build Image

The Ufora build image is based on Ubuntu-14.04. To download it to your local docker image repository:

```bash
$ sudo docker pull ufora/build
```

To see the downloaded images, run:

```bash
$ sudo docker images | grep ufora
ufora/build           latest           7405aad675a3        2 days ago          1.569 GB
```
The output should look something like the above though the number and ids of images will vary over time.

To try it out run:

```bash
$ sudo docker run -it --rm=true ufora/build bash
root@4cdcdd1b4d6c: 
```

**Congratulations!** You now have a container running an interactive `bash` session in on Ubuntu 14.04.
You can terminate the container at any time by exiting the bash session (i.e. `$ exit`).

**Note:** Any changes you make to the state of the container (e.g. installing packages, editing files, etc.)
are lost when you exit the container due to the `--rm=true` argument, which tells docker to delete the container when it exits.


# Setup Mounted Volumes

Docker lets you share directories between containers and the host.
This is done using [Volumes](https://docs.docker.com/userguide/dockervolumes/).

There are many ways to work with volumes in docker.
One of the easiest and most convenient ways is by creating a container on your machine that maps one
or more directories from your host file-system into docker volumes.
You can then easily mount all volumes from that data container into any new containers you launch.

Start by creating a directory in your host file-system that will act as your mount point:

```bash
$ mkdir ~/volumes
```

Pull the base Ubuntu-14.04 image if you haven't already done so:

```
$ sudo docker pull ubuntu:14.04
Pulling repository ubuntu
5ba9dab47459: Download complete
511136ea3c5a: Download complete
27d47432a69b: Download complete
5f92234dcf1e: Download complete
51a9c7c1f8bb: Download complete
```

Create a named, daemonized container called `DATA` and mount your volumes directory into it:

```bash
$ sudo docker run -d --name DATA -v /home/user/volumes:/volumes ubuntu:14.04
051f5275583c726d80a7a484a5fea01a580c3f2900ee6ee93130d84be10cd9e7
```

The `-v` argument defines a mapping between a path in the host file-system and the container.
In the example above, the directory `/home/user/volumes/` will appear in the container under `/volumes`.

You can now run containers and map volumes from `DATA` into them using docker's `--volumes-from` option. For example:

```bash
$ touch ~/volumes/test.file
$ sudo docker run -it --volumes-from DATA ufora/build bash
> ls /volumes
test.file
> touch /volumes/test2.file
> exit
$ ls ~/volumes
test.file test2.file
```

# Clone the Ufora Repo

You will want to have a clone of the repo inside your volumes directory.
The easiest way is to simply create a new clone:

```bash
$ git clone git@github.com:ufora/main.git ~/volumes/src
```

Note that you cannot create a symbolic link to an existing repo inside your volumes directory because
the link will not be resolvable inside docker containers.
If you absolutely must expose an existing directory, you can either add it as another volume in your `DATA` container,
or use `mount --bind` to mount it into a subdirectory of `~/volumes`.
Note that if you use the `mount` approach, the newly mounted directory will be visible to new containers,
but not to ones that were already running when the directory was mounted.


# Running a Dev Container

You are now ready to launch a container from the image you downloaded.
The [`docker run`](https://docs.docker.com/reference/run/) command is used to create a container from a specified image and run a command in it.

To launch a container run:

```bash
$ sudo docker run -it --volumes-from DATA -p 30000:30000 --privileged=true --rm=true ufora/build bash
```

Let's take a look at the arguments:

* `-it` - runs the container interactively in the terminal (and creates a pseudo-tty)
* `--volumes-from DATA` - mount all volumes mounted to the container named "DATA"
* `-p 30000:30000` - map port 30000 in the container (the HTTP port of the Ufora GUI) to the same port in the host OS.
  This lets you run Python code that uses the `pyfora` package on your host OS and connect to the Ufora
  backedn running in the container using `pyfora.connect('http://localhost:30000')`.
* `--privileged=true` - run the container in privileged mode.
    This is necessary if you want to use `gdb` to debug processes inside the container.
* `--rm=true` - delete the container when it exists.

You are now in a bash session inside your newly launched container and are ready to build.


# Building the Project

To build the project run (replacing `/volumes/src` with the mount point of your repo):

```bash
> cd /volumes/src
> export PYTHONPATH=`pwd`
> ./waf configure
> ufora/scripts/resetAxiomSearchFunction.py
> ./waf install
> ufora/scripts/rebuildAxiomSearchFunction.py
> ./waf install
```

This will take between 12 and 30 minutes, depending on the speed of your computer.

Notice that we run a two-phase build. Some source files are generated, but the generator itself
uses the Ufora shared-object. We first build with a stub version of the generated code, then run
the code-generator (line 4) to produce the "real" code and then build again. The second build should be
*much* faster.

You only need to run `resetAxiomSearchFunction.py` when you build a clean repo for the first time,
and you only need to run `rebuildAxiomSearchFunction.py` after pulling a new revision or if you
makde changes to `AxiomSearch.cpp` or `AxiomSearch2.cpp` in `/ufora/Fora/Axioms/`.


# Running the Ufora Services

You will need to set a couple of environment variables, install `node.js` modules required by the
web front-end, and install the `pyfora` package in development mode.
Assuming you mounted your repo to `/volumes/src`, run:

```bash
> cd /volumes/src
> export PYTHONPATH=`pwd`
> export ROOT_DATA_DIR=/volumes/ufora
> pip install -e packages/python
> cd ufora/web/relay
> npm install
```

Start the ufora backend services and a worker:

```bash
> cd /volumes/src
> ufora/scripts/init/start
> ufora/scripts/init/ufora-worker start
```

The Ufora services should now be running using the `forever` watchdog service.
To list all running services run:

```bash
> forever list
info:    Forever processes running
data:        uid  command script                                                                           forever pid  id logfile                               uptime
data:    [0] 7xUM python  /volumes/src/ufora/distributed/SharedState/sharedStateMainline.py --logging=info 1047    1063    /volumes/ufora/logs/ufora-store.log   0:0:1:41.859
data:    [1] __r7 python  /volumes/src/ufora/scripts/init/ufora-gateway.py                                 1068    1085    /volumes/ufora/logs/ufora-gateway.log 0:0:1:41.611
data:    [2] wCvy coffee  /volumes/src/ufora/web/relay/server.coffee --gatewayport=30008 --port=30000      1090    1099    /volumes/ufora/logs/ufora-web.log     0:0:1:41.365
data:    [3] QEGg python  /volumes/src/ufora/scripts/init/ufora-worker.py                                  1176    1181    /volumes/ufora/logs/ufora-worker.log  0:0:0:3.301
```

The service logs are placed in the `logs` directory of `ROOT_DATA_DIR`.

# Stopping the Ufora Services

To stop all Ufora services run:

```bash
> forever stopall
```

# Running Tests

The main entry point for running tests is the script `test.py` at the root of the repo.
Tests are broken up into several categories:

- `native`: C++ unit tests
- `lang`: Unit tests for the fora language.
- `py`: Python unit tests - these are the majority of tests. These are all single-process tests.
- `scripts`: Multi-process tests that run a full Ufora backend. The test scripts live in the repo
             under `/test_scripts/`.

You can run **all** test by running:

```bash
python test.py
```

However, running *all* tests can take a *very* long time on a single machine.
You can also run a single test category with:

```bash
python test.py -native

python test.py -lang

python test.py -py [-filter=test_name] [-modpair i n]

python test.py -scripts [--scriptPath test_scripts/<path>]
```


# CCache

The Ufora dev image has `ccache` installed and configured to use `/volumes/ccache` as its cache directory.
This allows you to reuse the cache across container instances and also speeds up the build within a container
because mounted volumes don't use docker's AUFS layered file-system.
If you mount your volumes to a directory other than `/volumes`,
you will need to set the `CCACHE_DIR` environment variable accordingly.
