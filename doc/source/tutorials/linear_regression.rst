Linear Regression
=================

This tutorial demonstrates using :mod:`pyfora` to:
    1. Load a large CSV file from Amazon S3
    2. Parse it into a :class:`pandas.DataFrame`
    3. Run linear regression on the loaded DataFrame
    4. Download the regression coefficients and intercept back to python


.. important::
    The example below uses a **large** dataset. It is a 64GB csv file that parses into 20GB
    of normally-distributed, randomly generated floating point numbers.
    It takes about 8 minutes to run on three c3.8xlarge instances in EC2.

    You can use the :py:data:`pyfora_aws` script installed with the :mod:`pyfora` package to easily
    set up a Ufora cluster in EC2 using either on-demand or spot instances.

    If you prefer to try a (much) smaller version of this example, you can use the 5.2GB dataset
    ``iid-normal-floats-13mm-by-17.csv``, by modifying line 9 below accordingly.


.. code-block:: python
   :linenos:

    import pyfora
    from pyfora.pandas_util import read_csv_from_string
    from pyfora.algorithms import linearRegression

    print "Connecting..."
    ufora = pyfora.connect('http://<ufora_cluster_manager>:30000')
    print "Mapping data..."
    raw_data = ufora.importS3Dataset('ufora-test-data',
                                     'iid-normal-floats-20GB-20-columns.csv').result()

    print "Parsing and regressing..."
    with ufora.remotely:
        data_frame = read_csv_from_string(raw_data)
        predictors = data_frame.iloc[:, :-1]
        responses = data_frame.iloc[:, :-1:]

        regression_result = linearRegression(predictors, responses)
        coefficients = regression_result[:-1]
        intercept = regression_result[-1]


    print 'coefficients:', coefficients.toLocal().result()
    print 'intercept:', intercept.toLocal().result()


If you are familiar with :mod:`pandas` the code above should look quite familiar.
After connecting to a Ufora cluster using :func:`pyfora.connect` in line 6, we import a dataset
from Amazon S3 in line 8 using :func:`~pyfora.Executor.Executor.importS3Dataset`.


The value :py:data:`raw_data` returned from :func:`~pyfora.Executor.Executor.importS3Dataset` is a
:class:`~pyfora.RemotePythonObject.RemotePythonObject` that represents the entire dataset as a string.
The data itself is lazily loaded to memory in the cluster when it is needed.

All the code inside the ``with ufora.remotely:`` block that starts in line 12 is shipped to the cluster
and executes remotely.

We use :func:`~pyfora.pandas_util.read_csv_from_string` to read the CSV in :py:data:`raw_data` and
produce a DataFrame.

Our regression fits a linear model to predict the last column from the prior ones.
The :func:`~pyfora.algorithms.linearRegression` algorithm is used to return an array with the linear
model's coefficients and intercept.

In lines 22 and 23, outside the ``with ufora.remotely:`` block, we bring some of the values computed
remotely back into the local python environment.
Values assigned to variables inside the ``with ufora.remotely:`` are left in the Ufora cluster
by default because they can be very large - much larger than the amount of memory available on your
machine. Instead, they are represented locally using :class:`~pyfora.RemotePythonObject.RemotePythonObject`
instances that can be downloaded using their :func:`~pyfora.RemotePythonObject.RemotePythonObject.toLocal`
function.
