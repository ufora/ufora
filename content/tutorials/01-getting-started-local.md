---
layout: main
title: Getting Started Locally
tagline: How to Run Ufora on One Machine Using Docker
category: tutorial
---


You can easily run the Ufora backend locally on your machine using [docker](http://www.docker.com/).
Then you can connect pyfora to your local backend and start using it to speed up your python code.

# What You Need to Get Started
## OS
You'll need an OS that can run docker. Currently this means:

- A reasonably recent version of a 64-bit Linux distribution such as: Ubuntu, Debian, RedHat, Fedora, Centos, Gentoo, Suse, Amazon, Oracle, etc.
- OS X 10.8 "*Mountain Lion*" or newer.
- Windows 7.1, 8/8.1 or newer.


## Python
Ufora's python client, `pyfora`, requires CPython 2.7.

**Note:** Python 3 is not supported yet.

**Important:** Only official CPython distributions from python.org are supported at this time.
This is what OS X and most Linux distributions include by default as their "native" Python.


# Install pyfora

```bash
$ [sudo] pip install pyfora [--upgrade]
```

# Install Docker
Docker is available for Linux, OS X, or Windows. To install docker on your machine, visit [http://www.docker.com/](http://www.docker.com/), click the *Get Started* link, and follow the instructions.

You can also, optionally, follow [these instructions](http://askubuntu.com/a/477554) to be able to run docker commands without `sudo`. Note, however, that the docker daemon still runs as `root` - it just saves you five keystrokes when running docker commands.


# Pull the Ufora Service Image
Once docker is installed, you can pull the Ufora service image. You will need to use an image compatible with your version of pyfora.
To find the version of pyfora you have installed you can run the following command from your terminal:

```bash
$ python -c "import pyfora; print pyfora.__version__"
0.1
```

Now pull the ufora service image with the same version number. For example, if you are using pyfora version `0.1`, run:

```bash
$ [sudo] docker pull ufora/service:0.1
```

**Note:** Depending on your docker setup, you may need to run the last command, and subsequent docker commands, as `root`, by using `sudo`, for example.


You can also combine the last two commands into a one-liner:

```bash
$ [sudo] docker pull ufora/service:`python -c "import pyfora; print pyfora.__version__"`
```


# Start the Ufora Container

The command below starts an all-in-one docker container that runs all the Ufora backend services needed to support pyfora. To run a Ufora cluster on multiple machines in a local network, follow the instructions [here](getting-started-cluster.html).

Create a local directory for the Ufora service logs:

```bash
$ mkdir ~/ufora
```

From your terminal run:

```bash
$ [sudo] docker run -d --name ufora -p 30000:30000 -v /home/user/ufora:/var/ufora ufora/service:0.1
```

Replace the path `/home/user` with your own home directory path.

**What does this do?**

- `docker run` launches a new docker container.
- `-d` starts the container as daemon that runs in the background.
- `--name ufora` names the new container `ufora` for easy reference in subsequent commands.
- `-p 30000:30000` maps port 30000 - Ufora's default HTTP port - to the same port number in your host OS.
This lets `pyfora` connect to the container using `http://localhost:30000`.
- `-v /home/user/ufora:/var/ufora` mounts the local directory `~/ufora` into `/var/ufora` within the container.
This is where Ufora writes all of its log files.
- `ufora/service:0.1` is the name (and version tag) of the Ufora service image to run.


# Run Some Code

You are now ready to connect `pyfora` to your running container and run some code.
Create a new Python file called `tryfora.py` with the following content:

{% highlight python linenos=table %}
import pyfora

ufora = pyfora.connect('http://localhost:30000')

def isPrime(p):
    x = 2
    while x*x <= p:
        if p%x == 0:
            return 0
        x = x + 1
    return 1

print "Counting primes..."
with ufora.remotely.downloadAll():
    result = sum(isPrime(x) for x in xrange(10 * 1000 * 1000))

print result
{% endhighlight %}

**Congratulations!** You just ran your first Ufora computations and counted
the number of primes between 0 and 10 million. The computation inside the
`with` block (line 15) was shipped to the Ufora worker running in the docker
container, which then compiled it to efficient machine code and ran it
parallel on all cores available on your machine.

**Important:** At this point `pyfora` cannot be used interactively in the Python REPL. You MUST place your code in a .py file and run it from there.


# Stop the Ufora Container

When you are done and want to stop the Ufora service container, run:

```bash
$ [sudo] docker stop ufora
```

This stops the container but does preserves its state so it can be restarted at a later time.

To permanently delete the container and all its state, run the following command after stopping the container:

```bash
$ [sudo] docker rm ufora
```


# Restart the Ufora Container

To restart a stopped Ufora service container, run:

```bash
$ [sudo] docker start ufora
```
