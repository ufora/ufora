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

"""
CacheSemantics

Class to process a FORA cachecall
"""

import ufora.native.FORA as ForaNative
import ufora.config.Setup as Setup
import ufora.distributed.S3 as S3


class InvalidCacheCall(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class CacheCallEntry(object):
    """represents a 'CacheCall' lookup in FORA.

    agent - the object being called
    args - the arguments to apply to it
    nearnessIndicator - the cache-hint provided by user code, or None
    """
    def __init__(self, agent, args, nearnessIndicator):
        self.agent = agent
        self.args = args
        self.nearnessIndicator = nearnessIndicator

    @staticmethod
    def fromCacheCallTupleEntry(cacheCallTupleElement):
        """process a tuple of cache-call arguments passed as an ImplValContainer"""
        assert isinstance(cacheCallTupleElement, ForaNative.ImplValContainer)

        if  cacheCallTupleElement.getTuple() is None:
            raise InvalidCacheCall("Cache-call argument must be a tuple")

        if len(cacheCallTupleElement) not in (2,3):
            raise InvalidCacheCall("Cache-call tuple must contain two or three elements")

        agent = cacheCallTupleElement[0]
        args = cacheCallTupleElement[1]

        if cacheCallTupleElement[1].getTuple() is None:
            raise InvalidCacheCall("Cache-call arguments must be a tuple")

        nearness = None

        return CacheCallEntry(agent, args, nearness)

    def extractApplyTuple(self):
        """return a list of the actual FORA elements that make up the evaluation call"""
        args = [self.agent, ForaNative.makeSymbol("Call")]
        args.extend(self.args)
        return tuple(args)

def processCacheCall(cacheCallElement):
    """process a tuple of cache-call arguments passed as an ImplValContainer"""
    assert isinstance(cacheCallElement, ForaNative.ImplValContainer)
    return [CacheCallEntry.fromCacheCallTupleEntry(x) for x in cacheCallElement]


def getCurrentS3Interface():
    return S3.getFactoryFromConfig(Setup.config())

def isCacheRequestWithResult(cacheCallElement):
    assert isinstance(cacheCallElement, ForaNative.ImplValContainer)

    return len(cacheCallElement) == 3 and \
        cacheCallElement[0] == ForaNative.makeSymbol("S3Dataset")

def getAppropriateChunksForSize(size, chunkSize):
    chunks = []
    curIx = 0

    while curIx < size:
        top = min(curIx + chunkSize, size)
        chunks.append((curIx, top))
        curIx = top

    if len(chunks) > 1 and (chunks[-1][1] - chunks[-1][0]) < chunkSize / 2:
        newLow = chunks[-2][0]
        newHigh = chunks[-1][1]

        chunks[-2:] = [(newLow, newHigh)]

    return chunks

def getCacheRequestComputationResult(cacheCallElement):
    bucketname = cacheCallElement[1].pyvalOrNone
    keyname = cacheCallElement[2].pyvalOrNone

    if not isinstance(bucketname, str) or not isinstance(keyname, str):
        return ForaNative.ComputationResult.Exception(
            ForaNative.ImplValContainer("Badly formed S3 dataset request: %s" % cacheCallElement)
            )

    s3Interface = getCurrentS3Interface()

    if s3Interface.keyExists(bucketname, keyname):
        keysAndSizesMatching = [(keyname, s3Interface.getKeySize(bucketname, keyname))]
    else:
        keysAndSizesMatching = s3Interface.listKeysWithPrefix(bucketname, keyname + "_")

        indicesKeysAndSizes = []

        for key, size, mtime in keysAndSizesMatching:
            try:
                index = int(key[len(keyname)+1:])
                indicesKeysAndSizes.append((index, key, size))
            except ValueError:
                pass

        keysAndSizesMatching = [(key, size) for _, key, size in sorted(indicesKeysAndSizes)]

    if not keysAndSizesMatching:
        return ForaNative.ComputationResult.Exception(
            ForaNative.ImplValContainer("No keys matching %s/%s using %s" % (
                bucketname,
                keyname,
                s3Interface
                ))
            )

    wholeVectorIVC = ForaNative.getEmptyVector()

    for key, size in keysAndSizesMatching:
        CHUNK_SIZE = 10 * 1024 * 1024

        chunks = getAppropriateChunksForSize(size, CHUNK_SIZE)

        for lowIndex, highIndex in chunks:
            externalDatasetDesc = ForaNative.ExternalDatasetDescriptor.S3Dataset(
                bucketname,
                key,
                lowIndex,
                highIndex
                )

            vectorDataId = ForaNative.VectorDataID.External(externalDatasetDesc)

            vectorIVC = ForaNative.createFORAFreeBinaryVector(vectorDataId, highIndex - lowIndex)

            wholeVectorIVC = ForaNative.concatenateVectors(wholeVectorIVC, vectorIVC)

    return ForaNative.ComputationResult.Result(wholeVectorIVC, ForaNative.ImplValContainer())



