Linear Regression
=================

This tutorial demonstrates using :mod:`pyfora` to:
    1. Load a CSV file from Amazon S3
    2. Parse it into a :class:`pandas.DataFrame`
    3. Run a linear regression on the loaded DataFrame
    4. Download the regression coefficients and intercept back to python


.. code-block:: python
   :linenos:

    import pyfora
    import pyfora.pandas_util
    from pyfora.algorithms import linearRegression

    import pandas

    ufora = pyfora.connect('http://<ufora_cluster_manager>:30000')
    raw_data = ufora.importS3Dataset("ufora-test-data", 'iid-normal-floats-13mm-by-17').result()

    with ufora.remotely:
        data_frame = pyfora.pandas_util.read_csv_from_string(raw_data)
        predictors = pandas.DataFrame(data_frame._columns[:-1])
        responses = pandas.DataFrame(data_frame._columns[-1:])

        regression_result = linearRegression(predictors, responses)
        coefficients = regression_result[:-1]
        intercept = regression_result[-1:]


    print "coefficients:", coefficients.toLocal().result()
    print "intercept:", intercept.toLocal().result()


If you are familiar with :mod:`pandas` and :mod:`sklearn`, the code above should look quite familiar.
After connecting to a Ufora cluster using :func:`pyfora.connect` in line 7, we import a dataset
from Amazon S3 in line 8 using :func:`~pyfora.Executor.Executor.importS3Dataset`.

The dataset used in this example is a 20GB set of normally-distributed, randomly generated floating
point numbers in CSV format with 20 columns and 13-million rows.

The value :py:data:`raw_data` returned from :func:`~pyfora.Executor.Executor.importS3Dataset` is a
:class:`~pyfora.RemotePythonObject.RemotePythonObject` that represents the entire dataset as a string.
The data itself is lazily loaded to memory in the cluster when it is needed.

All the code inside the ``with ufora.remotely:`` block that starts in line 10 is shipped to the cluster
and executes remotely.

We use :func:`~pyfora.pandas_util.read_csv_from_string` to read the CSV in :py:data:`raw_data` and
produce a DataFrame.

Our regression fits a linear model to predict the last column from the prior ones.
The :func:`~pyfora.algorithms.linearRegression` algorithm is used to return an array with the linear
model's coefficients and intercept.

In lines 20 and 21, outside the ``with ufora.remotely:`` block, we bring some of the values computed
remotely back into the local python environment.
Values assigned to variables inside the ``with ufora.remotely:`` are left in the Ufora cluster
by default because they can be very large - much larger than the amount of memory available on your
machine. Instead, they are represented locally using :class:`~pyfora.RemotePythonObject.RemotePythonObject`
instances that can be downloaded using their :func:`~pyfora.RemotePythonObject.RemotePythonObject.toLocal`
function.
