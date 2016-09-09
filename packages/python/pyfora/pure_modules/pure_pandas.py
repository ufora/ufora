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


from pyfora.PureImplementationMapping import PureImplementationMapping, pureMapping
from pyfora.pure_modules.pure_numpy import PurePythonNumpyArray

from pyfora.unique import unique
import numpy

import pandas


#######################################
# PurePython implementations:
#######################################

@pureMapping(pandas.DataFrame)
class _DataframeFactory(object):
    def __call__(self, data):
        return PurePythonDataFrame(data)


class PurePythonDataFrame(object):
    def __init__(self, data, columns=None):
        if columns is None and isinstance(data, PurePythonDataFrame):
            self._columnNames = data._columnNames
            self._columns = data._columns
        elif isinstance(data, dict):
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

        raise ValueError("value " + str(k) + " is not a column name")

    def pyfora_addColumn(self, columnName, column):
        assert not columnName in self._columnNames

        return PurePythonDataFrame(
            self._columns + [column],
            self._columnNames + [columnName]
            )

    def as_matrix(self):
        columnMajorData = []
        for col in self._columns:
            columnMajorData = columnMajorData + col.tolist()

        tr = PurePythonNumpyArray((len(columnMajorData),), columnMajorData)
        # currently, PurePythonNumpyArrays are row-major,
        # so we form the transpose here
        tr = tr.reshape((self.shape[1], self.shape[0]))
        return tr.transpose()

    def apply(self, func, axis):
        if axis == 0:
            raise NotImplementedError()
        elif axis == 1:
            return PurePythonSeries(
                [func(self.iloc[ix]) for ix in xrange(len(self))]
                )
        else:
            raise TypeError("no axis " + str(axis))

    def dot(self, other, _splitLimit=1000000):
        # we're currently only imagining 1-dimensional `other`s

        assert self.shape[1] == len(other)

        return PurePythonSeries(self._dot(other, _splitLimit, 0, self.shape[0]))

    def columns(self):
        # NOTE: this is not pandas-API compatible.
        return self._columns

    def _dot(self, other, splitLimit, low, high):
        sz = high - low
        if sz <= splitLimit:
            return self._dot_on_chunk(other, low, high)

        mid = (high + low) / 2
        return self._dot(other, splitLimit, low, mid) + \
            self._dot(other, splitLimit, mid, high)

    def _dot_on_chunk(self, other, low, high):
        tr = _scaleVecOnRange(self._columns[0], other[0], low, high)

        colIx = 1
        while colIx < self.shape[1]:
            tr = _addVecsOnRange(
                tr, self._columns[colIx], other[colIx], low, high)
            colIx = colIx + 1

        return tr


def _scaleVecOnRange(vec, multiplier, lowIx, highIx):
    tr = []
    ix = lowIx
    while ix < highIx:
        tr = tr + [multiplier * vec[ix]]
        ix = ix + 1

    return tr

def _addVecsOnRange(vec1, vec2, vec2Multiplier, lowIx, highIx):
    tr = []
    ix = lowIx

    while ix < highIx:
        tr = tr + [vec1[ix - lowIx] + vec2Multiplier * vec2[ix]]
        ix = ix + 1

    return tr



class _PurePythonDataFrameILocIndexer(object):
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, k):
        if isinstance(k, tuple):
            return self.getitem_tuple(k)
        elif isinstance(k, slice):
            return self.getitem_tuple((k, slice(None, None, None)))
        elif isinstance(k, int):
            return self.get_ix(k)
        else:
            raise IndexError("don't know how to index with " + str(k))

    def getitem_tuple(self, tup):
        if len(tup) == 1:
            tup = (tup[0], slice(None, None, None))

        if isinstance(tup[1], int) and isinstance(tup[0], (int, slice)):
            return self.obj._columns[tup[1]][tup[0]]
        elif isinstance(tup[0], slice) and isinstance(tup[1], slice):
            return PurePythonDataFrame(
                [col[tup[0]] for col in self.obj._columns[tup[1]]],
                self.obj._columnNames[tup[1]]
                )
        else:
            raise IndexError("don't know how to index with " + str(tup))

    def get_ix(self, ix):
        return PurePythonSeries(
            _DataFrameRow(self.obj, ix)
            )


class _DataFrameRow(object):
    def __init__(self, df, rowIx, startColumnIx=0, size=None, stride=1):
        self.df = df
        self.rowIx = rowIx
        self.startColumnIx = startColumnIx
        if size is None:
            size = df.shape[1]
        self.size = size
        self.stride = stride

    def __len__(self):
        return self.size

    def __getitem__(self, ix):
        if isinstance(ix, int):
            return self._get_int_ix(ix)
        elif isinstance(ix, slice):
            raise NotImplementedError()
        else:
            raise TypeError("don't know how to __getitem__ with " + str(ix))

    def _get_int_ix(self, ix):
        if ix >= 0:
            assert ix < self.size
            columnIx = self.startColumnIx + ix * self.stride
        else:
            assert ix > -self.size
            columnIx = self.startColumnIx + (self.size + ix) * self.stride

        return self.df.iloc[self.rowIx, columnIx]

    def __iter__(self):
        for ix in xrange(len(self)):
            yield self._get_int_ix(ix)


class _PurePythonSeriesIlocIndexer(object):
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, k):
        return self.obj[k]


@pureMapping(pandas.Series)
class _PurePythonSeriesFactory(object):
    def __call__(self, arg):
        return PurePythonSeries(arg)


class PurePythonSeries(object):
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

    def tolist(self):
        try:
            isinstance(self.values, list)
        except:
            raise Exception(type(self.values))

        if isinstance(self.values, list):
            return self.values
        elif isinstance(self.values, PurePythonNumpyArray):
            return self.values.tolist()
        else:
            return [self[ix] for ix in xrange(len(self))]

    def as_matrix(self):
        return PurePythonNumpyArray((len(self),), self.tolist())

    def unique(self):
        sortedSeries = self.sort_values()
        return unique(sortedSeries.values, True)

    def sort_values(self):
        return PurePythonSeries(sorted(self.values))

    @property
    def iloc(self):
        return _PurePythonSeriesIlocIndexer(self)

    def __add__(self, other):
        if isinstance(other, PurePythonSeries):
            assert len(self) == len(other)

            return PurePythonSeries(
                [ self[ix] + other[ix] for ix in xrange(len(self))]
                )

        return PurePythonSeries(
            [elt + other for elt in self]
            )

    def __iter__(self):
        for ix in xrange(len(self)):
            yield self[ix]

    def __pyfora_generator__(self):
        return self.values.__pyfora_generator__()

    def apply(self, func):
        return PurePythonSeries(
            [func(elt) for elt in self]
            )

    def dot(self, other):
        return numpy.dot(self, other)

#######################################
# PureImplementationMappings:
#######################################

@pureMapping
class PurePythonSeriesMapping(PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [pandas.Series]

    def getMappableInstances(self):
        return []

    def getPurePythonTypes(self):
        return [PurePythonSeries]

    def mapPythonInstanceToPyforaInstance(self, pandasSeries):
        return PurePythonSeries(pandasSeries.tolist())

    def mapPyforaInstanceToPythonInstance(self, pureSeries):
        return pandas.Series(pureSeries.values)


@pureMapping
class PurePythonDataFrameMapping(PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [pandas.DataFrame]

    def getMappableInstances(self):
        return []

    def getPurePythonTypes(self):
        return [PurePythonDataFrame]

    def mapPythonInstanceToPyforaInstance(self, pandasDataFrame):
        return PurePythonDataFrame({
            name: pandasDataFrame[name] for name in pandasDataFrame
            })

    def mapPyforaInstanceToPythonInstance(self, pureDataFrame):
        return pandas.DataFrame({
            name: pureDataFrame[name] for name in pureDataFrame._columnNames
            })

