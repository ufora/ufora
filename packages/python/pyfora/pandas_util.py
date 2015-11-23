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

import pyfora.typeConverters.PurePandas as PurePandas


def readCsvFromString(data):
    """
    `readCsvFromString`: read a python csv string into a `PurePythonDataFrame`

    Arguments:
        `data`: a string of comma-separated values

    Returns:
        a `PurePythonDataFrame`, which holds the parsed data.

    NOTE: this currently assumes that all values are float (or floatifiable), 
        and that the first row contains headers.
        
    """
    listOfColumns, columnNames = \
        PurePandas.PurePythonDataFrame.__pyfora_builtins__.readCsvFromString(
            data
            )

    return PurePandas.PurePythonDataFrame(
        listOfColumns, columnNames
        )

