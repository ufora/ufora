---
layout: main
title: Getting Started on AWS
tagline: How to Boot Ufora Instances on Amazon EC2
category: tutorial
---


If you have an [Amazon Web Services](https://aws.amazon.com/) account you can get started with
running Ufora at scale within minutes.

The `pyfora` package includes an auxiliary script called `pyfora_aws` that helps with getting started
on AWS.


# What You Need to Get Started
## AWS Account
You'll need an [AWS](https://aws.amazon.com/) account with an access key that has permission to launch EC2 instances. If don't yet have an access key, follow [these instructions](https://aws.amazon.com/developers/access-keys/) to create one.

## Python
Ufora's python client, `pyfora`, requires CPython 2.7.

**Note:** Python 3 is not supported yet.

**Important:** Only official CPython distributions from python.org are supported at this time.
This is what OS X and most Linux distributions include by default as their "native" Python.


# Install pyfora

```bash
$ [sudo] pip install pyfora [--upgrade]
```

# Launch Ufora Instances

## Credentials
We use [Boto](https://boto.readthedocs.org/en/latest/) to interact with EC2 on your behalf.
If you already have a [Boto configuration file](http://boto.readthedocs.org/en/latest/boto_config_tut.html)
with your credentials then no additional configuration in needed.
Otherwise, you can set your credentials using the environment variables: AWS_ACCESS_KEY_ID, and AWS_SECRET_ACCESS_KEY.

To set the envrionment variables, open a terminal window and type:

```bash
$ export AWS_ACCESS_KEY_ID=<your aws access key id>
$ export AWS_SECRET_ACCESS_KEY=<your aws secret key>
```

## Start Ufora Instance

You are now ready to start some instances using `pyfora_aws`. In the same terminal window run:

```bash
$ pyfora_aws start --ec2-region <region>
Launching ufora manager...
Ufora manager started:
    i-90c57f54 | 52.26.77.142 | running | manager
```

Where `<region>` is the name of an AWS region (e.g. `us-west-2`, `eu-central-1`, etc.)

This command starts one on-demand `c3.8xlarge` instance and configure it to run the Ufora backend.
It may take a couple of minutes to run.
The first two segments in the last line of output are the EC2 instance-id and the instance's public IP address.

For a full description of `pyfora_aws` and its various options see [this page](../documentation/pyfora-aws.html).


# Run Some Code

You are now ready to connect `pyfora` to your running instance and run some code.

Create a new Python file called `tryfora.py` with the following content, replacing `<ip_address>`
with the public IP address of your running instance:

{% highlight python linenos=table %}
import pyfora

ufora = pyfora.connect('http://<ip_address>:30000')

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
`with` block (line 15) was shipped to the Ufora cluster running in AWS, which
then compiled it to efficient machine code and ran it parallel on all cores
available on your machine.

**Important:** At this point `pyfora` cannot be used interactively in the Python REPL. You MUST place your code in a .py file and run it from there.


# Stop Ufora Instance

To stop all your running Ufora instances, run:

```bash
$ pyfora_aws stop --ec2-region <region>
```
