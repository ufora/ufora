pyfora - Compiled, parallel python
==================================

pyfora is the client package for Ufora_ - a compiled, automatically parallel Python for data science
and numerical computing.

Ufora achieves speed and scale by reasoning about your python code to compile
it to machine code (so it's fast) and find parallelism in it (so that it scales).  The Ufora
runtime is fully fault tolerant, and handles all the details of data
management and task scheduling transparently to the user.

The Ufora runtime is invoked by enclosing code in a "ufora.remote" block. Code
and objects are shipped to a Ufora cluster and executed in parallel across
those machines. Results are then injected back into the host python
environment either as native python objects, or as  handles (in case the
objects are very large).  This allows you to pick the subset of your code that
will benefit from running in Ufora - the remainder can run in your regular
python environment.

For all of this to work properly, Ufora places one major restriction on
the code that it runs: it must be "pure", meaning that it cannot modify data
structures or have side effects.  This restriction allows the Ufora runtime to
agressively reorder calculations, which is crucial for
parallelism, and allows it to perform compile-time
optimizations than would not be possible otherwise. For more on the subset of python
that Ufora supports, see `python restrictions`_.

.. _python restrictions: https://ufora.github.io/ufora/documentation/python-restrictions.html


Installation
============

The pyfora client is a pure python package and can be installed by running:

.. code::

    pip install pyfora


Getting Started with Ufora
==========================

The ufora backend is available as a docker image that can be run locally on your machine, or in a 
cluster of machines on a local network or in the cloud.

- `Getting started with local Ufora`_
- `Getting started with Ufora on AWS`_
- `Running Ufora on a local cluster`_


.. _Getting started with local Ufora: https://ufora.github.io/ufora/tutorials/getting-started-local.html
.. _Getting started with Ufora on AWS: https://ufora.github.io/ufora/tutorials/getting-started-aws.html
.. _Running Ufora on a local cluster: https://ufora.github.io/ufora/tutorials/getting-started-cluster.html


Credits
-------

Pyfora is developed and maintained by the Ufora_ team. Find us on Github_.


- `Distribute`_

.. _Distribute: http://pypi.python.org/pypi/distribute

.. _Ufora: https://ufora.github.io/ufora
.. _Github: https://github.com/ufora/ufora
