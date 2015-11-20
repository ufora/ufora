.. role:: python(code)
   :language: python

Introduction to pyfora
======================

Pyfora is a python package for running code on a Ufora_ cluster, where it is compiled and can be
automatically parallelized. With pyfora you can run computations on a cluster of machines without
having to modify your code. You can speed up your computations by running them on hundreds of CPU cores,
and you can operate on datasets many times larger than the RAM of a single machine.


.. _Ufora: https://ufora.github.io/ufora


Setting up a Ufora Cluster
--------------------------

To get started with pyfora you will need a Ufora cluster with at least one worker.
The ufora backend is available as a docker_ image that can be run locally on your machine in a
single-node setup, or on a cluster of machines on a local network or in the cloud.

- `Getting started with local Ufora`_
- `Running a Ufora cluster`_
- `Getting started with Ufora on AWS`_


.. _docker: https://www.docker.com/
.. _Getting started with local Ufora: https://ufora.github.io/ufora/tutorials/getting-started-local.html
.. _Getting started with Ufora on AWS: https://ufora.github.io/ufora/tutorials/getting-started-aws.html
.. _Running a Ufora cluster: https://ufora.github.io/ufora/tutorials/getting-started-cluster.html


Connecting to a Cluster
-----------------------

Once you have a running Ufora cluster, you can connect to it and start executing code::

    import pyfora
    ufora = pyfora.connect('http://localhost:30000')

The variable :py:data:`ufora` is now bound to pyfora :class:`~pyfora.Executor.Executor` that can be used
to submit and execute code on the cluster.
There are two ways to run code with an :class:`~pyfora.Executor.Executor`:

1. **Asynchronously** using :class:`~pyfora.Future.Future` objects.
2. **Synchronously** by enclosing code to be run remotely in a special python :py:data:`with` block.

In this tutorial we will use the synchronous model.

First, we'll define a function that we are going to work with::

    def isPrime(p):
        x = 2
        while x*x <= p:
            if p%x == 0:
                return 0
            x = x + 1
        return 1


Computing Remotely
------------------

Now we can use the :class:`~pyfora.Executor.Executor` to run some remote computations with the function
we defined::

    with ufora.remotely.downloadAll():
        result = sum(isPrime(x) for x in xrange(10 * 1000 * 1000))

    print result


What just happened?
~~~~~~~~~~~~~~~~~~~

The code in the body of the :py:const:`with` block was shipped to the Ufora cluster, along with any dependent
objects and code (like :py:func:`isPrime` in this case) that it refers to, directly or indirectly.

The python code was translated into Ufora bitcode and executed by the Ufora runtime. The resulting
objects (:py:data:`result` in the example above) were downloaded from the cluster and copied back
back into the local python environment because we used
:func:`ufora.remotely.downloadAll() <pyfora.WithBlockExecutor.WithBlockExecutor.downloadAll>`.

Depending on the code you are running, and the number of CPU cores available in your cluster, the
Ufora runtime looks for opportunities to parallelize the execution of your code.
In the example above Ufora can see that individual invocations of :py:func:`isPrime` within the generator
expression :python:`isPrime(x) for x in xrange(10 * 1000 * 1000)` are independent of each other can therefore
be run in parallel.

In fact, what Ufora does in this example is to split the :py:func:`xrange` iteration across all available
cores in the cluster. If a particular subrange completes while others are still running, Ufora 
dynamically subdivides a range that is still computing to maximize the utilization of CPUs.
This is something that is bound to happen in problems like this when time-complexity of a computation
is not constant across the entire input space (determining whether a large number is prime is much
harder than a small number).


.. note::
    Not **all** python code can be converted to Ufora bitcode and run in this way.
    In order to benefit form the performance and scalability advantages of Ufora, your code must be:

    1. **Side-effectless**: data structures cannot be mutated.
    2. **Deterministic**: running with the same input must always yield the same result.

    See :ref:`pure-python-label` for more details.


Working with proxies
~~~~~~~~~~~~~~~~~~~~
In the previous example, the result of the computation was the number of prime numbers in the specified
range. That's a single :py:obj:`int` that can be easily downloaded from the cluster and copied into
the local python environment.

Now consider this variation of the code::

    with ufora.remotely.remoteAll():
        primes = [x for x in xrange(10 * 1000 * 1000) if isPrime(x)]

This time the result of the computation is a :py:obj:`list` of all prime numbers in the range.
But because we used 
:func:`ufora.remotely.remoteAll() <pyfora.WithBlockExecutor.WithBlockExecutor.remoteAll>`,
the variable :py:data:`primes` is a *proxy* to a list of primes that lives in-memory on the Ufora
cluster (it is actually an instance of :class:`~pyfora.RemotePythonObject.RemotePythonObject`).

There are two things you can do with remote python objects:

1. Download them into the local python scope where they become regular python objects.
2. Use them in subsequent remote computations on the Ufora cluster.

Downloading a remote object is done using its :func:`~pyfora.RemotePythonObject.RemotePythonObject.toLocal`
method, which returns a :class:`~pyfora.Future.Future` that resolves to the downloaded object.
To do it all synchronously you might write::

    primes = primes.toLocal().result()

This call downloads all the data in the remote :py:data:`primes` list from the Ufora cluster to the
client machine where it is converted back into python. If the list is very large, or the connection
to the cluster is slow, this can be a slow operation.
Furthermore, the size of the list may be greater than the amount of memory available on the local
machine, in which case it is impossible to download it this way.

As an alternative to downloading the entire result, we may choose to compute with it inside of 
another :python:`with ufora.remotely` block. For example::

    with ufora.remotely.downloadAll():
        lastFewPrimes = primes[-100:]

Ufora recognizes that :py:data:`primes` is a proxy to data that lives remotely in the cluster, and
lets us refer to it in dependent computations, which we then return as regular python objects.

For convenience, it also possible to write::

    with ufora.remotely.downloadSmall(bytecount=100*1024):
        ...

In this case, objects larger than :py:data:`bytecount` are left in the cluster and returned as proxies,
while smaller objects are downloaded and copied into the local scope.



.. _pure-python-label:

Pure Python
-----------
The Ufora runtime supports a restricted, "purely functional" subset of python that we call "Pure Python".
By "purely functional" we mean code in which:

- All data-structures are immutable (e.g. no modification of lists).
- No operations have side-effects (e.g. no sockets, no :py:func:`print`).
- All operations are deterministic - running them on the same input always yields the same result
  (e.g. no access to system time, amount of available memory, etc.)

These restrictions are essential to the kinds of reasoning that Ufora applies to your code.
Some of these restrictions may be relaxed in the future under certain circumstances, but at this
time the following constraints are enforced:

- **Objects are immutable** (except for :py:const:`self` within an object's :py:func:`__init__`).
  Expressions like :python:`obj.x = 10` are disallowed, as they would modify :py:data:`obj`.
  The exception to this rule is :py:const:`self` within :py:func:`__init__`, where assignments
  are used to provide initial values to object members.

- **Lists are immutable**. Expressions like :python:`a[0] = 10` won't work, nor will :python:`a.append(10)`.

  **However**, given a list :py:data:`a`, "appending" a value :py:data:`x` to it by producing a new list
  using :python:`a + [x]` results in effecient code without superflous copying of data.

- **Dictionaries are immutable**. In the future, updates to dictionaries will be allowed in cases
  where Ufora can prove that there is exactly one reference to the dictionary. But for the moment
  dictionaries can only be constructed from iterators, as in::

    dict((x, x**2) for x in xrange(100))

  Also note that at the moment, dictionaries can be quite slow, so use them sparingly.

- **No augmented assignment**. Expressions like :python:`x += 10` are disallowed since they modify
  :py:data:`x`.

- :py:func:`print` is disabled.

- :py:func:`locals` and :py:func:`globals` are disabled.

- :py:const:`del` is disabled.

- No :py:func:`eval` or :py:func:`exec`.

.. note::
   Regular variable assignments **do** work as expected. The following code, for example, is allowed::

       x = x + 5
       v = [x]
       v = v + [12]


Violation of constraints
~~~~~~~~~~~~~~~~~~~~~~~~

Whenever you invoke Ufora on a block of python code, Ufora attempts to give you either (a) the exact same
answer you would have received had you run the same code in your python interpreter locally,
or (b) an exception [#integer_arithmetic]_.

Constraint checking happens in two places. Some of the constraints are enforced at parse-time.
As soon as you enter a :python:`with ufora.remotely` block, Ufora tries to determine all the code your
invocation can touch. If any of that code contains syntatic elements that Ufora knows are invalid
(such as :py:func:`print` statements), it will generate an exception.

Other constraints are enforced at runtime. For instance, the append method of lists, when invoked in Ufora,
raises a :exc:`~pyfora.InvalidPyforaOperation` exception that's not catchable by python
code running inside of Ufora.  This indicates that the program has attempted to execute semantics that
Ufora can't faithfully reproduce.




.. rubric:: Footnotes

.. [#integer_arithmetic] Currently, the only intended exception to this rule is integer arithmetic:
    on the occurrence of an integer arithmetic overflow, Ufora will give you the semantics of the underyling hardware,
    whereas python will produce an object of type :py:const:`long` with the correct value.
    Eventually, we will make this tradeoff configurable, but it has pretty serious performance implications,
    so for the moment we're just ignoring this difference.
