# Ufora

Ufora is compiled, automatically parallel python for data science and
numerical computing.

## Why Ufora?

There are lots of tools and frameworks for data science at scale. Some of
these systems are very powerful, but they're also pretty cumbersome. They can
be hard to set up, and maintain, hard to learn, and your work isn't portable.
But we use them because we have no other choice.

But what if you had an infinitely fast computer, with an infinite amount of RAM?
Wouldn't you rather just write a simple python program to do your analysis?

This the Ufora dream: weave together hundreds of individual machines so that
they look and feel like one big, fast machine that you can program in regular
python.  

Ufora is still evolving, but it already achieves much of this goal:
Ufora can execute many programs hundreds or thousands of times faster
than in a regular python interpreter, and can operate on datasets many times
larger than the memory provided by a single machine. See [this page](https://ufora.github.io/ufora/github-pages/tutorial/basic-execution.html)
for a very simple example of what it looks like.

## How does it work?

Ufora achieves speed and scale by reasoning about your python code to compile
it (so it's fast) and find parallelism in it (so that it scales).  The Ufora
runtime is fully fault tolerant, and handles all the details of data
management and task scheduling transparently to the user.

Ufora is invoked from a host python interpreter. Code enclosed within a
`ufora.remote` block is shipped to a Ufora cluster and executed in parallel
across those machines. Results are then injected back into the host python
environment either as native python objects, or as  handles (in case the
objects are very large).  This allows you to pick the subset of your code that
will benefit from running in Ufora - the remainder can run in your regular
python environment.

For all of this to work properly, Ufora must place one major restriction on
the code that it runs: it must be "pure", meaning that it cannot modify data
structures or have side effects.  This restriction allows the Ufora runtime to
determine which calculations can be reordered which is crucial for
parallelism, and allows it to perform more agressive compile-time
optimizations than would be possible otherwise. For more on the subset of python
that Ufora supports, look [here](https://ufora.github.io/ufora/github-pages/documentation/python-restrictions.html).

## How can I deploy ufora?

The ufora front-end runs anywhere you can get a CPython interpreter - it's pure
python, installed using `pip`.

The ufora backend can be deployed three ways: you can stand up a "cluster" consisting of just a
(single machine)[https://ufora.github.io/ufora/github-pages/tutorials/getting-started-local.html), 
you can create a cluster in the cloud (e.g., (AWS)[https://ufora.github.io/ufora/github-pages/tutorials/getting-started-aws.html)), 
or you can set up a cluster on a grid of machines in your datacenter.  The backend currently builds on linux. We maintain
docker images of the latest builds so you can get going quickly, as well as an image you can build ufora in yourself.

## How can I get involved?

Users of the Ufora platform should visit [ufora-users](https://groups.google.com/forum/#!forum/ufora-user). Developers
should visit [ufora-dev](https://groups.google.com/forum/#!forum/ufora-dev)

The development of Ufora is ongoing, and led by [Ufora Inc.](http://www.ufora.com/). Drop us
a line if you'd like to get involved or need support.  


