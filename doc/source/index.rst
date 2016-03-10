.. pyfora documentation master file, created by
   sphinx-quickstart on Thu Nov 12 12:45:41 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


pyfora
======

Compiled, automatically parallel Python for data-science
--------------------------------------------------------

Any code you run with pyfora works as-is in python, but with pyfora it can run hundreds
or thousands of times faster, and can operate on datasets many times larger than the RAM of a single machine.
You can speed up your computations by running them on hundreds of CPU cores with terabytes of RAM,
and you can do this with hardly any changes to your code.

pyfora consists of two main components:

* A distributed backend that runs on one or more machines in your local network or in the cloud.
* A Python package that sends your code to the backend for compilation and execution.


Example
^^^^^^^

The following program uses pyfora to sum ``math.sin()`` over the first billion integers::

   import math, pyfora
   executor = pyfora.connect('http://localhost:30000')

   with executor.remotely.downloadAll():
      x = sum(math.sin(i) for i in xrange(10**9))

   print x


This program runs in **13.76 seconds** on a 3.40GHz Intel(R) Core(TM) i7-2600 quad-core
(8 hyperthreaded) CPU, and utilizes all 8 cores.
The same program in the local python interpreter takes **185.95 seconds** and uses one core.





Installation
^^^^^^^^^^^^
.. sourcecode:: bash

    pip install pyfora


pyfora requires Python 2.7. Python 3 is not supported yet.

.. note::
   Only official CPython distributions from python.org are supported at this time.
   This is what OS X and most Linux distributions include by default as their "system" Python.


Backend Installation
^^^^^^^^^^^^^^^^^^^^

The pyfora backend is distributed as a docker_ image that can be run in any docker-supported environment.
The :ref:`setup_guides` below contain instructions for setting up the backend in various environments.

.. _docker: https://www.docker.com/

.. _setup_guides:
.. toctree::
   :maxdepth: 1
   :caption: Setup Guides

   tutorials/aws
   tutorials/onebox
   tutorials/cluster


.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials/intro
   tutorials/performance
   tutorials/s3
   tutorials/linear_regression


.. toctree::
   :maxdepth: 2
   :caption: Tools

   reference/pyfora_aws

.. toctree::
   :maxdepth: 2
   :caption: Library Reference

   api


* :ref:`genindex`

