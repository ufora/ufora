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


import pyfora.PureImplementationMapping as PureImplementationMapping


def pd():
    import pandas
    return pandas


#######################################
# PurePython implementations:
#######################################

class _DataframeFactory:
    def __call__(self, data):
        return PurePythonDataFrame(data)


class PurePythonDataFrame:
    def __init__(self, data, columns=None):
        if isinstance(data, dict):
            self._columnNames = data.keys()
            self._columns = [PurePythonSeries(val) for val in data.values()]
        elif isinstance(data, list):
            # note this is not pandas-compliant:
            # in pandas, a list of lists describes *rows*
            if columns is None:
                columns = PurePythonDataFrame._defaultNames(len(data))

            self._columnNames = columns
            self._columns = [PurePythonSeries(col) for col in data]
        else:
            raise Exception("haven't dealt with this case yet")

        self._numColumns = len(self._columns)

        # TODO: some verification of numRows ...
        self._numRows = len(self._columns[0])

    @staticmethod
    def _defaultNames(numNames):
        return ["C" + str(ix) for ix in xrange(numNames)]

    # in Pandas, this is a classmethod, but we don't support those yet in PurePython
    @staticmethod
    def from_items(items):
        """
        [(colname, col), ... ] -> DataFrame
        """
        listOfColumns = [_[1] for _ in items]
        columnNames = [_[0] for _ in items]

        return PurePythonDataFrame(
            listOfColumns,
            columnNames
            )

    @property
    def shape(self):
        return (self._numRows, self._numColumns)

    @property
    def iloc(self):
        return _PurePythonDataFrameILocIndexer(self)

    def __len__(self):
        return self.shape[0]

    def __getitem__(self, k):
        colIx = self._columnIndex(k)
        return self._columns[colIx]

    def _columnIndex(self, k):
        for colIx in range(self._numColumns):
            if k == self._columnNames[colIx]:
                return colIx

        raise ValueError("value " + str() + " is not a column name")


class _PurePythonDataFrameILocIndexer:
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, k):
        if isinstance(k, tuple):
            return self._getitem_tuple(k)
        else:
            raise NotImplementedError("only implementing getitems for tuples right now")

    def _getitem_tuple(self, tup):
        if len(tup) != 2:
            raise IndexError("tuple indexing only supported for length-two tuples")

        if isinstance(tup[1], int) and isinstance(tup[0], (int, slice)):
            return self.obj._columns[tup[1]][tup[0]]
        elif isinstance(tup[0], slice) and isinstance(tup[1], slice):
            return PurePythonDataFrame(
                [col[tup[0]] for col in self.obj._columns[tup[1]]],
                self.obj._columnNames[tup[1]]
                )
        else:
            raise IndexError("don't know how to index with " + str(tup))


class _PurePythonSeriesIlocIndexer:
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, k):
        return self.obj[k]


class PurePythonSeries:
    def __init__(self, data):
        if isinstance(data, PurePythonSeries):
            self.values = data.values
        else:
            self.values = data

    def __len__(self):
        return len(self.values)

    def __getitem__(self, ix):
        if isinstance(ix, slice):
            return PurePythonSeries(self.values[ix])
        else:
            return self.values[ix]

    @property
    def iloc(self):
        return _PurePythonSeriesIlocIndexer(self)


#######################################
# PureImplementationMappings:
#######################################


class PurePythonSeriesMapping(PureImplementationMapping.PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [pd().Series]

    def getMappableInstances(self):
        return []

    def getPurePythonTypes(self):
        return [PurePythonSeries]

    def mapPythonInstanceToPyforaInstance(self, pandasSeries):
        return PurePythonSeries(list(pandasSeries.values))

    def mapPyforaInstanceToPythonInstance(self, pureSeries):
        return pd().Series(pureSeries.values)

class PurePythonDataFrameMapping(PureImplementationMapping.PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [pd().DataFrame]

    def getMappableInstances(self):
        return []

    def getPurePythonTypes(self):
        return [PurePythonDataFrame]

    def mapPythonInstanceToPyforaInstance(self, pandasDataFrame):
        return PurePythonDataFrame({
            name: pandasDataFrame[name] for name in pandasDataFrame
            })

    def mapPyforaInstanceToPythonInstance(self, pureDataFrame):
        return pd().DataFrame({
            name: pureDataFrame[name] for name in pureDataFrame._columnNames
            })

def mappings_():
    return [(pd().DataFrame, _DataframeFactory)]


def generateMappings():
    tr = [PureImplementationMapping.InstanceMapping(instance, pureType) for \
          (instance, pureType) in mappings_()]
    tr = tr + [PurePythonDataFrameMapping(), PurePythonSeriesMapping()]
    return tr
