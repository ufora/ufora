.. pyfora documentation master file, created by
   sphinx-quickstart on Thu Nov 12 12:45:41 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


pyfora
======

Compiled, automatically parallel Python for data-science
--------------------------------------------------------

Any code you run with :mod:`pyfora` will work unmodified in python.
But with :mod:`pyfora`, it can run hundreds or thousands of times faster,
and can operate on datasets many times larger than the RAM of a single machine.


:mod:`pyfora` requires Python 2.7.

**Note:** Python 3 is not supported yet.

.. note:: Only official CPython distributions from python.org are supported at this time. This is what OS X and most Linux distributions include by default as their "native" Python.


Installation
^^^^^^^^^^^^
.. sourcecode:: bash

    pip install pyfora


Backend Installation
^^^^^^^^^^^^^^^^^^^^

:mod:`pyfora` connects to a cluster of one or more machines that compile and run your code in parallel.
The backend is distributed as a docker_ image that can be run in any docker-supported environment.

.. _docker: https://www.docker.com/


On AWS
""""""

Using the :mod:`pyfora_aws` tool, included in the :mod:`pyfora` package, it is possible to setup
a cluster of any size on Amazon Web Services within minutes. See :doc:`tutorials/aws`.



On Linux with Docker
""""""""""""""""""""



Contents:

.. toctree::
   :maxdepth: 2

   tutorials

   reference/pyfora_aws

   api


* :ref:`genindex`

