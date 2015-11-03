---
layout: main
title: Getting Started with Docker
tagline: How to run a Ufora worker locally with Docker
---

You can easily run the Ufora backend locally on your machine using [docker](http://www.docker.com/).
Then you can connect pyfora to your local backend and start using it to speed up your python code.


# Install docker
Docker is available for Linux, OS X, or Windows. To install docker on your machine, visit [http://www.docker.com/](http://www.docker.com/), click the *Get Started* link, and follow the instructions.

You can also, optionally, follow [these instructions](http://askubuntu.com/a/477554) to be able to run docker commands without `sudo`. Note, however, that the docker daemon still runs as `root` - it just saves you five keystrokes when running docker commands.


# Pull the Ufora service image
Once docker is installed, you can pull the Ufora service image. You will need to use an image compatible with your version of pyfora.
To find the version of pyfora you have installed you can run the following command from your terminal:

```sh
$ python -c "import pyfora; print pyfora.__version__"
0.1
```

Now pull the ufora service image with the same version number. For example, if you are using pyfora version `0.1`, run:

```sh
$ docker pull ufora/service:0.1
```

**Note:** Depending on your docker setup, you may need to run the last command, and subsequent docker commands, as `root`, by using `sudo`, for example.


# Start the Ufora container

The command below starts an all-in-one docker container that runs all the Ufora backend services needed to support pyfora. To run a Ufora cluster on multiple machines in a local network, follow the instructions [here](getting-started-cluster.html).

Create a local directory for the Ufora service logs:

```sh
$ mkdir ~/ufora
```

From your terminal run:

```sh
$ docker run -d --name ufora -p 30000:30000 -v ~/ufora:/var/ufora ufora/service:0.1
```

**What does this do?**

- `docker run` launches a new docker container.
- `-d` starts the container as daemon that runs in the background.
- `--name ufora` names the new container `ufora` for easy reference in subsequent commands.
- `-p 30000:30000` maps port 30000 - Ufora's default HTTP port - to the same port number in your host OS.
This lets `pyfora` connect to the container using `http://localhost:30000`.
- `-v ~/ufora:/var/ufora` mounts the local directory `~/ufora` into `/var/ufora` within the container.
This is where Ufora writes all of its log files.
- `ufora/service:0.1` is the name (and version tag) of the Ufora service image to run.


# Run some code

You are now ready to connect `pyfora` to your running container and run some code.
Create a new Python file called `tryfora.py` with the following content:

```py
import pyfora

connection = pyfora.connect('http://localhost:30000')

# TODO: put sample code here...
```

**Important:** At this point `pyfora` cannot be used interactively in the Python REPL. You MUST place your code in a .py file and run it from there.


# Stop the Ufora container

When you are done and want to stop the Ufora service container, run:

```sh
$ docker stop ufora
```

This stops the container but does preserves its state so it can be restarted at a later time.

To permanently delete the container and all its state, run the following command after stopping the container:

```sh
$ docker rm ufora
```


# Restart the Ufora Container

To restarted a stopped Ufora service container, run:

```sh
$ docker start ufora
```
