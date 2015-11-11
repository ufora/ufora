---
layout: main
title: Getting Started With a Ufora Cluster
tagline: How to Run a Ufora Cluster on a Local Network
category: tutorial
---


# Before You Begin

This tutorial walks you through installing the Ufora backend on a cluster of machines.
If you have not read through the
[Getting Started Locally]({{ site.baseurl }}/content/tutorials/01-getting-started-local.html)
tutorial yet, it is recommended that you familiarize yourself with it before continuing with the
multi-machine setup.


# Ufora Cluster Toplogy

A Ufora cluster consists of a single *manager* and one or more *workers*. Workers contribute 
CPU and memory resources to the cluster and are where all computations take place.
Workers connect to the manager and register themselves with it. They use the manager to discover
each other's network addresses and port configuration and to find out when new workers join the cluster.

The manager, in addition to acting as a registry of workers, also acts as the cluster's front end.
A Ufora client machine, where you use the `pyfora` package to submit computations to a cluster
only ever talks to the cluster's manager. Workers only communicate with each other and with their manager.
The `pyfora` package connects to the manager over HTTP using [socket.io](http://socket.io/) to support real time
notifications from the cluster.


# The Ufora Docker Image

In the [Getting Started Locally]({{ site.baseurl }}/content/tutorials/01-getting-started-local.html)
tutorial you used the `ufora/service` docker image to start a container that ran both the manager and a worker on your
local machine. The same image can be configured to run a worker that connects to a specified manager
or, optionally, run the manager without a worker.

## Environment Variables

There are several environment variable that can be set when launching a Ufora container to configure
its behavior.

- `UFORA_MANAGER_ADDRESS` - the host-name or IP address of the Ufora manager.
    Setting this variable causes the container to only run the worker service.
    Without this variable, the container runs **both** manager and worker services.
- `UFORA_WORKER_OWN_ADDRESS` - the host-name or IP address that the Ufora worker uses to register itself
    with the manager. Other workers will try to connect to it using this address.
    This is useful in situations where you have multiple network interfaces
    (public and private, or a docker container running in bridge mode) and you want to tell the
    worker which address to register. The variable is optional and if omitted, the worker tries to
    figure out its own address using `socket.gethostbyname(socket.getfqdn())`.
- `UFORA_WORKER_BASE_PORT` - the first of two consecutive ports that the worker listens on. This is
    useful if you want to run multiple workers side-by-side.
- `UFORA_NO_WORKER` - Set this variable to `1` to prevent the manager container from also running a worker.
    This variable and `UFORA_MANAGER_ADDRESS` are mutually exclusive. At most one of them can be set.
- `UFORA_WEB_HTTP_PORT` - the port used by the manager's HTTP server.


## Ports

### Worker
Ufora workers communicate with each other over two consecutively numbered ports. One port is used
to maintain a control channel over which they coordinate work, and the other is used as a data channel
where large chunks of data can be transmitted.

The default ports are: `30009` and `30010`.

They can be configured using the `UFORA_WORKER_BASE_PORT` environment variable.


### Manager
The manager listens on two ports. One is the worker registry service to which workers connect, and
the other is the HTTP server that clients connect to using the `pyfora` package.

The worker registry port is `30002` and is not currently configurable. A configuration option will
be added in a future release. This port only needs to be accessible to workers.

The default HTTP port is `30000` and is configured using the `UFORA_WEB_HTTP_PORT` environment variable.

### Security
If you run the cluster on a local, trusted network you may not need to worry about this and can skip
to the next section. If, however, you run your cluster in the cloud or a shared network, you may want 
to read on.

The Ufora services do not have any build-in authentication mechanisms. There is no notion of accounts,
credentials, logging-in, etc. If you have network access to the services, you can submit work.
It is therefore recommended that you configure firewall rules (or a security group on AWS) such that
only machines in the cluster can connect to your workers on their ports (30009, and 30010 by default),
and to your manager on the worker-registry port (30002).

To connect your `pyfora` client in a secure way, it is recommended that you tunnel your HTTP traffic
over SSH using the `-L port:host:hostport` option. For example, if your manager is running at
`54.144.209.248` you can map your local port `30000` to the same port on the manager using:

```bash
ssh user_name@54.144.209.248 -L 30000:localhost:30000
```

Now as long as your SSH session is open, you can connect to the manager using `localhost:30000`.



# Running the Services

The instructions below assume you have already installed docker and pulled the `ufora/service` image
on all machines in the cluster.

**Reminder:** Be sure you pull the version of the `ufora/service` image that matches the version of
    `pyfora` you are running on your client(s) (e.g. `docker pull ufora/service:0.1`).

While not strictly necessary, it is recommended that you create a directory on all your machines
which will be mounted to `/var/ufora` on all your Ufora containers. The Ufora services will write
their logs into it, and having it on the host machine can make accessing logs easier. The instructions
below assume this directory is `/home/user/ufora`, replace it with your own path when running the
commands.

## Manager

Pick a machine to run the manager service and run the following command to start the manager **and**
a worker on it:

```bash
sudo docker run -d --name ufora_manager -p 30000:30000 -p 30002:30002 -v /home/user/ufora:/var/ufora ufora/service:0.1
```

To run the manager service **without** a worker run:

```bash
sudo docker run -d --name ufora_manager -e UFORA_NO_WORKER=1 -p 30000:30000 -p 30002:30002 -v /home/user/ufora:/var/ufora ufora/service:0.1
```


## Worker

If your manager is running, for example, at `192.168.1.15`, start the Ufora worker using:

```bash
sudo docker run -d --name ufora_worker -e UFORA_MANAGER_ADDRESS=192.168.1.15 -p 30009:30009 -p 30010:30010 -v /home/user/ufora:/var/ufora ufora/service:0.1
```


# Connect to the Cluster

You can now use `pyfora` to connect to your cluster. Create a python script with the following code:

```python
import pyfora

ufora = pyfora.connect('http://192.168.1.15:30000')

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
```

Run it to submit your first computation to the cluster!


