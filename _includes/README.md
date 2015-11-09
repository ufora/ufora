# What is Ufora?

Ufora is a compiled, automatically parallel subset of python for data science
and numerical computing.

Any code you run with Ufora will work unmodified in python. But with Ufora, 
it can run hundreds or thousands of times faster, and can operate 
on datasets many times larger than the RAM of a single machine.

# How do I get started?

Client installation is through [pip](https://pip.readthedocs.org/en/stable/). 
Workers can be booted in the [cloud](https://ufora.github.io/ufora/content/tutorials/02-getting-started-aws.html), 
or [locally](https://ufora.github.io/ufora/content/tutorials/01-getting-started-local.html) using docker.

```bash
#install the pyfora front-end and boto.
pip install pyfora boto

#link to your AWS account
export AWS_ACCESS_KEY_ID=<your aws access key id>
export AWS_SECRET_ACCESS_KEY=<your aws secret key>

#boot some workers in aws. This can take a couple of minutes.
pyfora_aws start --ec2-region us-west-2 --num-instances 4 
```

Now we're ready to run some code:

```py
import pyfora

#stick the ip address from pyfora_aws here
ufora = pyfora.connect('http://<ip_address>:30000')

def isPrime(p):
	if p < 2: return 0
    x = 2
    while x*x <= p:
        if p%x == 0: return 0
        x = x + 1
    return 1

with ufora.remotely.downloadAll():
    result = sum(isPrime(x) for x in xrange(100 * 1000 * 1000))

print "found ", result, " primes between 0 and 100 million"
```

The `ufora.remotely.downloadAll()` block invokes Ufora. Without it,  python
takes about an hour to do this on a fast machine. With 4 `c3.8xlarge` boxes on
amazon, pyfora takes about 10 seconds. It's the same exact code, hundreds of times
faster.

# Project Roadmap

The current release, `0.1`, is an early release of the Ufora python functionality.
The core Ufora VM has been under development for years, but the python front-end
is new. 

As of the `0.1` release, most core python language features and primitives are
implemented, as are a few builtins (`sum`, `xrange`, `range`, etc.).

In the upcoming `0.2` release, we're planning on filling out some more of the
python builtins, implementing the basic functionality present in `numpy` and
`pandas`, and enabling a pathway to load data from amazon S3.

After that, we're considering some of the following: 

* Python 3 support
* Coverage for some core `scikit` data science algorithms (gbm, regressions, etc.)
* Execution of arbitrary python code out-of-process (for non-pure code we don't want to port)
* More generic model for import/export of data from the cluster.
* Enabling better feedback in the pyfora api for tracking progress of computations.

Please [let us know](https://groups.google.com/forum/#!topic/ufora-user/FyT9oUhEa0w) 
what you'd like to see next, or if you'd like to get involved.

# Read more

* A [more detailed tutorial on running python code](https://ufora.github.io/ufora/content/tutorials/03-running-python-code.html)
* Run Ufora on your [local machine](https://ufora.github.io/ufora/content/tutorials/01-getting-started-local.html)
* Configuring Ufora to run in [AWS](https://ufora.github.io/ufora/content/tutorials/02-getting-started-aws.html)
* The [restrictions](https://ufora.github.io/ufora/content/documentation/01-python-restrictions.html) we place on python so that this can all work.

# Contact us.

Users of the Ufora platform should visit [ufora-users](https://groups.google.com/forum/#!forum/ufora-user). Developers
should visit [ufora-dev](https://groups.google.com/forum/#!forum/ufora-dev).

The development of Ufora is ongoing, and led by [Ufora Inc.](http://www.ufora.com/). [Drop us
a line](mailto:info@ufora.com) if you'd like to get involved or need enterprise support.


