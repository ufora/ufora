---
layout: main
title: Welcome to Ufora
tagline: Scalable python
---

Ufora is compiled, automatically parallel python.  

Ufora can execute a subset of programs hundreds or thousands of times faster
than in a regular python interpreter, and can operate on datasets many times
larger than the memory provided by a single machine.

Ufora operates by reasoning about your python code to compile it (so it's
fast) and find parallelism in it (so that it scales). Ufora can execute this
code on a single machine, on a cluster of linux machines in your datacenter,
or in the cloud.  The Ufora runtime is fully fault tolerant, and handles all the
details of data management and task scheduling transparently.

Unlike other systems for working with large datasets, Ufora doesn't force you
into using a specific pattern for scalability (e.g. map-reduce). Instead, it
finds the parallelism in all the code you write - from your perspective, it's
just python, at scale.

The primary requirement for code running in Ufora is that it be "pure",
meaning that it cannot modify data structures or have side effects - it can
only calculate new values.  This restriction allows the Ufora runtime to
determine which calculations can be reordered which is crucial for
parallelism, and allows it to perform more agressive compile-time
optimizations than would be possible otherwise.

Ufora is invoked from a host python interpreter. Code enclosed within a
`ufora.remote` block is shipped to a Ufora server and executed. Results are
then injected back into the host python environment either as native python
objects, or as  handles (in case the objects are very large).  This allows you
to pick the subset of your code that will benefit from running in Ufora - the
remainder can run in your regular python environment.

The development of Ufora is led by [Ufora Inc.](http://www.ufora.com/). Drop us
a line if you'd like to get involved or need support.

