---
layout: main
title: Extending pyfora
tagline: Adding new libraries
category: develop
sort_index: 05
---

# How Libraries Work

Python has one of the richest ecosystems of libraries for data science around.
One of our goals with Ufora is for a large subset of data-analysis programs to run out-of-the-box
with minimal modification – so we need a way of running these libraries, and we want them to scale.

Many of these libraries won’t be automatically convertible by Ufora.
Sometimes, this is because they use features that break the Ufora VM’s parallelism (e.g. mutability, threads, etc.),
and sometimes this is because they are implemented in C or FORTRAN and then wrapped in python (e.g. numpy, pandas, most of scikit).
Either way, we need a way of letting programs that use them run in Ufora.

We have two main ways of handling a given library or function:

- **Wrapping.** We can produce an alternative implementation in [pure python](/documentation/python-restrictions.html),
    and swap that in when we see references to the library.
- **Out-of-process execution.** We can run the library function natively in python,
    marshalling objects from Ufora into a separate python process,
    executing the library, and then marshalling the results back.

The wrapping approach has some important advantages:

- It allows the library to benefit from all of Ufora’s optimizations, so that it can scale.
- In cases where library designers implemented the library in C, we can provide something that’s easier
    to read and modify (that’s why we use python in the first place, isn’t it?) without sacrificing speed.
- The library doesn’t need to be available on the worker machines because we’re shipping the code,
    so it simplifies deployment and configuration.

Of course, it has the drawback that each library has to be ported before it can be used.

The out-of-process approach has the obvious benefit that it’s simple.
Unfortunately, it has its own drawbacks:

- it can be slower because we have to marshal data across process boundaries.
- If the majority of the library’s CPU time is spent in python, you need separate processes for every
    thread because of the oft-maligned Global Interpreter Lock.
- We can’t parallelize within the call to the external code. So you have to batch up the parallelism yourself.
- We can’t interrupt running processes and migrate them from one machine to another, or subdivide running processes,
    so it can make load-balancing harder for the VM.
- It’s hard to provide good behavior when we run out of RAM.
- It limits the total amount of data we can work with for any one function call to something reasonably small.
- The library needs to be careful to be “deterministic”.
    If it produces different results for the same input on subsequent runs,
    then Ufora’s fault tolerance model will break.
    This can actually be a hard thing to guarantee, because plenty of standard python idioms
    are nondeterministic (e.g. order of items in a dictionary).

The out-of-process approach is much closer to what frameworks like hadoop or spark do – data transformations
are executed in a language or runtime that’s a black box to the framework (e.g. the “mappers” and “reducers” in map-reduce),
and the orchestration of the computation is handled by the framework itself.

We prefer the first approach: providing an alternative implementation in python and letting Ufora do its magic.


# Implementing Libraries

There are three ways to provide implementations for existing python functions:

- Provide a python implementation for a specific python object, say a function.
    This is how builtins like `any` are implemented.
- Provide a python implementation for a class of python objects.
    This also requires you to provide “translators” that can map to and from your class’ internals and
    the alternative-implementation’s internals.  This is how our implementation of `numpy` works, for instance.
- Map a python singleton directly to an object implemented in FORA. This is how most low-level builtin types are implemented.
    For instance, python’s `list` object is mapped directly to the object defined in ListType.fora.
    Most libraries won’t need this.


## Mapping a Singleton Using Python

A python singleton mapping consists of a class whose constructor takes no arguments.
Ufora will map all uses of the singleton to an instance of the class, and all instances of the class back to the singleton.
We then have to register the implementation with the converter.

Example: the [any](https://github.com/ufora/ufora/blob/0.1/packages/python/pyfora/BuiltinPureImplementationMappings.py#L45)
builtin is implemented this way.


## Mapping a class of objects

To map an entire class of objects, we need two things: an implementation of the class, and a converter.
The converter is required to convert instances of the two classes between each other.
The pure python implementation must contain only valid Ufora python code.

Example: this is how our [numpy](https://github.com/ufora/ufora/blob/0.1/packages/python/pyfora/typeConverters/PurePythonNumpyArray.py#L21)
wrpper works.


## Mapping a singleton to FORA

In the case of some builtins, you may need to implement the singleton as a FORA object.
This can require some care, because unlike converted python code, the FORA code has direct access to FORA primitives.
It’s important to ensure that all objects returned to callers have the “PyObjectBase” mixin
(e.g. that they are in fact FORA objects that look like python objects).

Example: [`ListType.fora`](https://github.com/ufora/ufora/blob/0.1/packages/python/pyfora/fora/purePython/ListType.fora#L17)


# Roadmap

We plan on implementing the machinery for the out-of-process approach within the next couple of releases,
because it provides an immediate and effective bootstrap for existing libraries.
We’re hard at work porting numpy, pandas, and select functions from scikit.
We’d love to get some help!

