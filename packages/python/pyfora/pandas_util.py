#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import pyfora.pure_modules.pure_pandas as PurePandas


def read_csv_from_string(data):
    """
    Reads a string in CSV format into a DataFrame. This function is similar to
    :func:`pandas.read_csv` but it takes a string as input instead of a file.

    This function is intended to be used in pyfora code that runs
    remotely in a pyfora cluster.


    Args:
        data (str): a string of comma-separated values

    Returns:
        A :class:`pandas.DataFrame` that holds the parsed data.


    Note:
        This function currently assumes that all values are of type float (or floatifiable),
        and that the first row contains column headers. This limitation will be
        removed in the near future.
    """
    listOfColumns, columnNames = \
        __inline_fora(
            """fun(@unnamed_args:(data), *args) {
                   let df = try {
                       parsing.csv(
                           data.@m,
                           defaultColumnType: { PyFloat(Float64(_)) }
                           );
                       } catch (e) {
                       throw Exception(PyString(String(e)))
                       }

                   let listOfColumns = PyList(
                       df.columns.apply(
                           fun(series) {
                               PyList(series.dataVec)
                               }
                           )
                       );

                  let columnNames = PyList(
                      df.columnNames ~~ { PyString(_) }
                      )

                  return PyTuple((listOfColumns, columnNames))
                  }"""
            )(data)

    return PurePandas.PurePythonDataFrame(
        listOfColumns, columnNames
        )

