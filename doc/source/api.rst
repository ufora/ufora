
Library Reference
=================


pyfora
------
.. automodule:: pyfora


**Example:**
The following code connects to a Ufora cluster and counts the number of
prime numbers between zero and 100M::

    import pyfora

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

.. autofunction:: pyfora.connect


Exceptions
----------
.. autoexception:: pyfora.PyforaError
.. autoexception:: pyfora.ConnectionError
.. autoexception:: pyfora.NotCallableError
.. autoexception:: pyfora.ComputationError
.. autoexception:: pyfora.PythonToForaConversionError
.. autoexception:: pyfora.ForaToPythonConversionError
.. autoexception:: pyfora.PyforaNotImplementedError
.. autoexception:: pyfora.InvalidPyforaOperation
.. autoexception:: pyfora.ResultExceededBytecountThreshold


Executor
--------
.. autoclass:: pyfora.Executor.Executor
    :members:


WithBlockExecutor
-----------------
.. autoclass:: pyfora.WithBlockExecutor.WithBlockExecutor
    :members:


RemotePythonObject
------------------
.. automodule:: pyfora.RemotePythonObject

.. autoclass:: pyfora.RemotePythonObject.RemotePythonObject
    :members:


RemotePythonObject.DefinedRemotePythonObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: pyfora.RemotePythonObject.DefinedRemotePythonObject
    :members:


RemotePythonObject.ComputedRemotePythonObject
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: pyfora.RemotePythonObject.ComputedRemotePythonObject
    :members:


Future
------
.. autoclass:: pyfora.Future.Future
   :show-inheritance:
   :members: cancel


Algorithms
----------

Linear Regression
~~~~~~~~~~~~~~~~~
.. autofunction:: pyfora.algorithms.linearRegression

Logistic Regression
~~~~~~~~~~~~~~~~~~~
.. autoclass:: pyfora.algorithms.BinaryLogisticRegressionFitter
   :members: fit
.. autoclass:: pyfora.algorithms.BinaryLogisticRegressionModel.BinaryLogisticRegressionModel
    :members:

Regression Trees
~~~~~~~~~~~~~~~~
.. autoclass:: pyfora.algorithms.regressionTrees.RegressionTree.RegressionTreeBuilder
  :members:

Gradient Boosting
~~~~~~~~~~~~~~~~
.. autoclass:: pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder.GradientBoostedRegressorBuilder
  :members:
.. autoclass:: pyfora.algorithms.regressionTrees.GradientBoostedClassifierBuilder.GradientBoostedClassifierBuilder
  :members:

Data Frames
-----------
.. autofunction:: pyfora.pandas_util.read_csv_from_string
