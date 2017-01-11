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
A ComputedGraph model wrapping up access to the FORA computation system.

Every node in this graph is either a terminal FORA value or it's an apply of another set of nodes.

"""

import logging
import ctypes

import ufora.FORA.python.Runtime as Runtime
import ufora.native.FORA as ForaNative
import ufora.native.Hash as Hash
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph

import ufora.core.math.StableHashFunction as StableHashFunction
import ufora.native.Cumulus as CumulusNative
import ufora.util.TypeAwareComparison as TypeAwareComparison
import ufora.BackendGateway.SubscribableWebObjects.Exceptions as Exceptions

import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.WriteToS3Task \
    as WriteToS3Task


ImplValContainer_ = ForaNative.ImplValContainer

#install a function to let us hash implvals
def hashImplValContainer(ivc, unhashableObjectPolicy):
    return "ImplValContainer:" + str(ivc.hash)

StableHashFunction.hashFunctionsByType[ImplValContainer_] = hashImplValContainer

import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway

def isComputedValue(o):
    return ComputedGraph.isLocation(o) and issubclass(o.__location_class__, ComputedValue)

def validateIsVectorIVC(ivc):
    return ivc.isVector()

MAX_BYTES_TO_RETURN_IN_JSON = 10000


class ComputedValueVector(ComputedGraph.Location):
    """A Location representing a loadable piece of data in the Gateway's RAM cache.

    Incrementing its request count causes it to try to be loaded, and decrementing
    it gets rid of the dependency.

    Clients can access the data as a numpy array or pull out individual FORA values.
    """
    vectorImplVal = ComputedGraph.Key(object, default = None, validator = validateIsVectorIVC)

    @ComputedGraph.Function
    def __getitem__(self, index):
        """if index is an integer, attempt to index into the vector.

        If index is a slice, produce a computed value with the sliced vector
        """
        if self.vectorImplVal is None:
            raise IndexError()

        if isinstance(index, slice):
            return ComputedValue(
                args = (
                    self.vectorImplVal,
                    ForaNative.makeSymbol("GetItemDeepcopied"),
                    ForaNative.ImplValContainer(index.start),
                    ForaNative.ImplValContainer(index.stop),
                    ForaNative.ImplValContainer(index.step)
                    )
                )

        if index < 0 or index >= self.elementCount:
            raise IndexError()

        return self.entireSlice.extractVectorItemAsIVC(index)

    @ComputedGraph.ExposedProperty()
    def elementCount(self):
        if self.vectorImplVal is None:
            return 0

        return self.vectorImplVal.getVectorSize()

    def entireSlice(self):
        return self.getMappableSlice(0, self.elementCount)

    def slicesByPage(self):
        if self.vectorImplVal is None:
            return []

        return [self.getMappableSlice(low,high) for low,high in
                    self.vectorImplVal.getVectorPageSliceRanges(
                        ComputedValueGateway.getGateway().vdm
                        )]

    @ComputedGraph.Function
    def getMappableSlice(self, lowIndex, highIndex):
        return ComputedValueVectorSlice(
            computedValueVector = self,
            lowIndex = lowIndex,
            highIndex = highIndex
            )

    @ComputedGraph.ExposedFunction(expandArgs=True)
    def getSlice(self, lowIndex, highIndex):
        return self.getMappableSlice(lowIndex, highIndex)

    def __str__(self):
        return "%s" % (self.vectorImplVal)

class ComputedValueVectorFromComputedValue(ComputedValueVector):
    computedValue = ComputedGraph.Key(object)

    def vectorImplVal(self):
        return self.computedValue.valueIVC


class ComputedValueVectorSlice(ComputedGraph.Location):
    computedValueVector = object
    lowIndex = object
    highIndex = object

    isLoaded = ComputedGraph.Mutable(lambda: False)

    @ComputedGraph.NotCached
    def vectorDataIds(self):
        if self.computedValueVector.vectorImplVal is None:
            return []

        return self.computedValueVector.vectorImplVal.getVectorDataIdsForSlice(
            self.lowIndex,
            self.highIndex,
            ComputedValueGateway.getGateway().vdm
            )

    def __str__(self):
        return "ComputedValueVectorSlice(%s, %s, %s)" % (
            self.computedValueVector,
            self.lowIndex,
            self.highIndex
            )

    @ComputedGraph.Function
    def extractVectorDataAsPythonArray(self):
        if self.computedValueVector.vectorImplVal is None:
            return None

        if len(self.vectorDataIds) > 0 and not self.isLoaded:
            return None

        result = ComputedValueGateway.getGateway().extractVectorDataAsPythonArray(
            self.computedValueVector,
            self.lowIndex,
            self.highIndex
            )

        if result is None and not self.vdmThinksIsLoaded():
            logging.info("CumulusClient: %s was marked loaded but returned None. reloading", self)
            self.isLoaded = False
            ComputedValueGateway.getGateway().reloadVector(self)

        return result

    @ComputedGraph.Function
    def vdmThinksIsLoaded(self):
        return ComputedValueGateway.getGateway().vectorDataIsLoaded(
                self.computedValueVector,
                self.lowIndex,
                self.highIndex
                )

    @ComputedGraph.Function
    def markLoaded(self, isLoaded):
        self.isLoaded = isLoaded

    @ComputedGraph.Function
    def extractVectorDataAsNumpyArray(self):
        logging.info("Extract numpy data for %s: %s", self, self.vdmThinksIsLoaded())
        if self.computedValueVector.vectorImplVal is None:
            return None
        
        if len(self.vectorDataIds) > 0 and not self.isLoaded:
            return None

        result = ComputedValueGateway.getGateway().extractVectorDataAsNumpyArray(
            self.computedValueVector,
            self.lowIndex,
            self.highIndex
            )

        if result is None and not self.vdmThinksIsLoaded():
            logging.info("CumulusClient: %s was marked loaded but returned None", self)
            self.isLoaded = False
            ComputedValueGateway.getGateway().reloadVector(self)

        return result

    @ComputedGraph.Function
    def extractVectorDataAsNumpyArrayInChunks(self, stepSize = 100000):
        """Return the data as a sequence of numpy arrays each of which is no larger than 'stepSize'.

        This is used to prevent us from creating memory fragmentation when we are loading
        lots of arrays of different sizes.
        """
        if self.computedValueVector.vectorImplVal is None:
            return None
        
        if len(self.vectorDataIds) > 0 and not self.isLoaded:
            return None

        if not self.vdmThinksIsLoaded():
            return None

        result = []
        index = self.lowIndex
        while index < self.highIndex and result is not None:
            tailResult = ComputedValueGateway.getGateway().extractVectorDataAsNumpyArray(
                self.computedValueVector,
                index,
                min(self.highIndex, index+stepSize)
                )
            index += stepSize
            if tailResult is not None:
                result.append(tailResult)
            else:
                result = None

        if result is None and not self.vdmThinksIsLoaded():
            logging.info("CumulusClient: %s was marked loaded but returned None", self)
            self.isLoaded = False
            ComputedValueGateway.getGateway().reloadVector(self)

        return result

    @ComputedGraph.Function
    def extractVectorItemAsIVC(self, ct):
        if self.computedValueVector.vectorImplVal is None:
            return None
        
        if len(self.vectorDataIds) > 0 and not self.isLoaded:
            return None

        result = ComputedValueGateway.getGateway().extractVectorItem(self.computedValueVector, ct)

        if result is None:
            logging.info("CumulusClient: %s was marked loaded but returned None", self)
            self.isLoaded = False
            ComputedValueGateway.getGateway().reloadVector(self)

        return result


    @ComputedGraph.ExposedFunction()
    def getSlice(self, lowIndex, highIndex):
        assert lowIndex >= 0
        assert lowIndex < highIndex
        assert highIndex <= self.highIndex - self.lowIndex

        return ComputedValueVectorSlice(
            computedValueVector = self.computedValueVector,
            lowIndex = self.lowIndex + lowIndex,
            highIndex = self.lowIndex + highIndex
            )

    @ComputedGraph.ExposedFunction()
    def increaseRequestCount(self, *args):
        """request the data in the leaf of this vector"""
        ComputedValueGateway.getGateway().increaseVectorRequestCount(self)

    @ComputedGraph.ExposedFunction()
    def decreaseRequestCount(self, *args):
        ComputedValueGateway.getGateway().decreaseVectorRequestCount(self)
        

def validateComputedValueArgs(args):
    """check that every argument to a ComputedValue is either an ImplValContainer or
        another ComputedValue"""

    if not args:
        return False
    if not isinstance(args, tuple):
        return False
    for ix, a in enumerate(args):
        if ComputedGraph.isLocation(a):
            if not issubclass(a.__location_class__, ComputedValue):
                logging.error("Failed validation of args[%s].__location_class__ = '%s'", ix, a.__location_class__)
                return False
        else:
            if not isinstance(a, (ImplValContainer_, long, int, str, bool)):
                logging.error("Failed validation of args[%s].__class__ = '%s'", ix, a.__class__)
                return False
    return True


class ComputedValue(ComputedGraph.Location):
    """Represents the description of a single Fora computation."""

    # A tuple that represents the axiom-like Fora expression to compute.
    # e.g. (implValForFunction, `Call, 1, 2)
    args = ComputedGraph.Key(object, default = None, validator = validateComputedValueArgs)

    # Result is an Interpreter::ComputationResult (defined in # ufora/FORA/Core/ComputationResult.hppml)
    # which may consist of an Exception, Result, or Failure.
    result = ComputedGraph.Mutable(lambda: None)

    computationStatistics = ComputedGraph.Mutable(lambda: None)

    def __hash__(self):
        return hash(self.hash)

    def __cmp__(self, other):
        self.depth
        return TypeAwareComparison.typecmp(self, other,
            lambda self, other : cmp(self.hash, other.hash))

    def depth(self):
        """compute the depth of the ComputedValue tree"""
        tr = 0
        if self.args is None:
            return 0

        for a in self.args:
            try:
                tr = max(a.depth + 1, tr)
            except AttributeError:
                pass

        assert tr < 50, self
        return tr

    @ComputedGraph.ExposedProperty()
    def asVector(self):
        if not self.isFinished:
            return None

        if self.isException:
            return None

        if not self.valueIVC.isVector():
            return None

        return ComputedValueVectorFromComputedValue(computedValue = self)

    def computationDefinitionTerm_(self):
        return CumulusNative.ComputationDefinitionTerm.Subcomputation(
            self.cumulusComputationDefinition.asRoot.terms
            )

    def cumulusComputationDefinition(self):
        terms = []

        assert self.args is not None, self.__location_class__

        for a in self.args:
            if isinstance(a, (long, int, str, bool)):
                terms.append(CumulusNative.ComputationDefinitionTerm.Value(ImplValContainer_(a), None))
            elif isinstance(a, ImplValContainer_):
                terms.append(CumulusNative.ComputationDefinitionTerm.Value(a, None))
            else:
                terms.append(a.computationDefinitionTerm_)

        return CumulusNative.ComputationDefinition.Root(
            CumulusNative.ImmutableTreeVectorOfComputationDefinitionTerm(terms)
            )

    @ComputedGraph.ExposedProperty()
    def submittedComputationId(self):
        computationId = ComputedValueGateway.getGateway().submittedComputationId(self.cumulusComputationDefinition)

        if computationId is None:
            return

        return computationId.toSimple()

    @ComputedGraph.ExposedFunction()
    def cancel(self, *args):
        ComputedValueGateway.getGateway().cancelComputation(self, self.cumulusComputationDefinition)

    @ComputedGraph.ExposedFunction()
    def requestComputationCheckpoint(self, *args):
        ComputedValueGateway.getGateway().requestComputationCheckpoint(self, self.cumulusComputationDefinition)

    @ComputedGraph.ExposedFunction()
    def increaseRequestCount(self, *args):
        ComputedValueGateway.getGateway().increaseRequestCount(self, self.cumulusComputationDefinition)

    @ComputedGraph.ExposedFunction()
    def triggerCompilation(self, *args):
        runtime = Runtime.getMainRuntime()
        axioms = runtime.getAxioms()
        compiler = runtime.getTypedForaCompiler()
        
        reasoner = ForaNative.SimpleForwardReasoner(compiler, axioms)
        
        frame = reasoner.reasonAboutComputationDefinition(self.cumulusComputationDefinition)

        logging.critical("Result was %s", frame.exits())


    @ComputedGraph.ExposedFunction()
    def decreaseRequestCount(self, *args):
        ComputedValueGateway.getGateway().decreaseRequestCount(self, self.cumulusComputationDefinition)


    def totalVectorBytesReferenced(self):
        if self.checkpointStatus is None:
            return 0

        stats = self.checkpointStatus.statistics
        
        return ComputedValueGateway.getGateway().bytecountForBigvecs(
                        self.checkpointStatus.bigvecsReferenced
                        )

    def totalBytesOfMemoryReferenced(self):
        if self.checkpointStatus is None:
            return 0

        stats = self.checkpointStatus.statistics
        
        return stats.totalBytesInMemory

    def isCompletelyCheckpointed(self):
        if self.checkpointStatus is None:
            return False

        stats = self.checkpointStatus.statistics

        totalSeconds = stats.timeElapsed.timeSpentInCompiledCode + stats.timeElapsed.timeSpentInInterpreter
        return self.totalComputeSecondsAtLastCheckpoint + 1.0 > totalSeconds

    @ComputedGraph.ExposedProperty()
    def unfinishedDependentCodeLocationsAsJson(self):
        res = []

        for cv in self.rootComputedValueDependencies:
            if not cv.isFinished:
                #each computed value we depend on might be a visualize. If so, we want
                #the actual script computation (if available)
                cv = cv.unwrapVisualizable

                cv = cv.unwrapMember

                #only some ComputedValue objects have this property
                loc = cv.codeLocationDefinitionAsJson
                if loc is not None:
                    res.append(loc)
                else:
                    res.append(str(ComputedGraph.getLocationTypeFromLocation(cv)))

        return tuple(res)


    @ComputedGraph.ExposedProperty()
    def stats(self):
        if self.checkpointStatus is None:
            return {}

        stats = self.checkpointStatus.statistics

        result = {
            "status": {
                "title" : "Computation Status",
                "value" : "Finished" if self.isFinished else "Unfinished" + 
                    ((" (%s cpus)" % self.totalWorkerCount) if self.totalWorkerCount > 0 else ""),
                "units" : ""
                },
            "cpus": {
                "title" : "Total CPUs",
                "value" : self.totalWorkerCount,
                "units" : ""
                },
            "timeSpentInCompiler": {
                "title" : "Time in compiled code (across all cores)",
                "value" : stats.timeElapsed.timeSpentInCompiledCode,
                "units" : "sec"
                },
            "timeSpentInInterpreter": {
                "title" : "Time in interpreted code (across all cores)",
                "value" : stats.timeElapsed.timeSpentInInterpreter,
                "units" : "sec"
                },
            "totalSplitCount": {
                "title" : "Total split count",
                "value" : stats.totalSplitCount,
                "units" : ""
                },
            "totalBytesReferenced": {
                "title" : "Total bytes referenced (calculations)",
                "value" : self.totalBytesOfMemoryReferenced,
                "units" : "bytes"
                },
            "totalBytesReferencedJustPaged": {
                "title" : "Total bytes referenced (vectors)",
                "value" : self.totalVectorBytesReferenced,
                "units" : "bytes"
                }
            }

        result["isCheckpointing"] = {
                "title" : "Is Checkpointing",
                "value" : self.isCheckpointing,
                "units" : ""
                }

        result["isLoadingFromCheckpoint"] = {
                "title" : "Is loading from checkpoint",
                "value" : self.isLoadingFromCheckpoint,
                "units" : ""
                }

        if self.totalBytesReferencedAtLastCheckpoint > 0:
            result["totalBytesReferencedAtLastCheckpoint"] = {
                'title': "Size of last checkpoint",
                'value': self.totalBytesReferencedAtLastCheckpoint,
                'units': 'bytes'
                }

        secondsAtCheckpoint = self.totalComputeSecondsAtLastCheckpoint

        if secondsAtCheckpoint == 0.0:
            result["checkpointStatus"] = {
                "title" : "Checkpoint Status",
                "value" : "not checkpointed",
                "units" : ""
                }
        else:
            totalSeconds = stats.timeElapsed.timeSpentInCompiledCode + stats.timeElapsed.timeSpentInInterpreter
            if secondsAtCheckpoint + 1.0 >= totalSeconds:
                result["checkpointStatus"] = {
                    "title" : "Checkpoint Status",
                    "value" : "Checkpointed",
                    "units" : ""
                    }
            else:
                result["checkpointStatus"] = {
                    "title" : "Uncheckpointed compute seconds",
                    "value" : totalSeconds - secondsAtCheckpoint,
                    "units" : "sec"
                    }

        return result

    def isFailure(self):
        if not self.result:
            return None

        return self.result.isFailure()

    def failure(self):
        if not self.result:
            return None

        return self.result.asFailure.error.toString()

    @ComputedGraph.ExposedProperty()
    def isException(self):
        if not self.result:
            return None

        return self.result.isException()

    def valueIVC(self):
        if not self.result:
            return None

        if self.result.isException():
            return self.result.asException.exception

        if self.result.isResult():
            return self.result.asResult.result

        return None

    @ComputedGraph.ExposedProperty()
    def isFinished(self):
        return self.valueIVC is not None or self.isFailure

    def isEmpty(self):
        if not self.isFinished:
            return True
        if self.isException:
            return False
        if self.isFailure:
            return False
        if self.valueIVC is None:
            return True
        if self.isVector:
            return self.valueIVC.getVectorSize() == 0
        if self.valueIVC.isNothing():
            return True
        if self.valueIVC.isString():
            return len(self.valueIVC.pyval) == 0
        if self.valueIVC.isTuple():
            return len(self.valueIVC) == 0
        return False

    workerCount = ComputedGraph.Mutable(object, lambda: 0)
    workerCountForDependentComputations = ComputedGraph.Mutable(object, lambda: 0)
    cacheloadCount = ComputedGraph.Mutable(object, lambda: 0)
    cacheloadCountForDependentComputations = ComputedGraph.Mutable(object, lambda: 0)
    checkpointStatus = ComputedGraph.Mutable(object, lambda: None)
    totalComputeSecondsAtLastCheckpoint = ComputedGraph.Mutable(object, lambda: 0.0)
    isCheckpointing = ComputedGraph.Mutable(object, lambda: False)
    isLoadingFromCheckpoint = ComputedGraph.Mutable(object, lambda: False)
    rootComputedValueDependencies = ComputedGraph.Mutable(object, lambda: ())
    totalBytesReferencedAtLastCheckpoint = ComputedGraph.Mutable(object, lambda: 0)
    
    @ComputedGraph.ExposedProperty()
    def totalWorkerCount(self):
        return self.workerCount + self.workerCountForDependentComputations

    def codeLocationDefinitionAsJson(self):
        return None
    
    @ComputedGraph.ExposedProperty()
    def totalCacheloadCount(self):
        return self.cacheloadCount + self.cacheloadCountForDependentComputations

    def __str__(self):
        if self.args is None:
            return "ComputedValue(None)"

        return "ComputedValue" + str(tuple(self.args))

    def hash(self):
        h0 = self.hashValue_(self.args[0])
        for arg in self.args[1:]:
            h0 = h0 + self.hashValue_(arg)
        return h0

    @ComputedGraph.Function
    def hashValue_(self, value):
        if hasattr(value, 'hash'):
            return value.hash

        logging.debug("Using python hash on type '%s'. %s", type(value), str(value))
        hashValue = ctypes.c_uint32(hash(value)).value
        return Hash.Hash(hashValue)

    def isVector(self):
        if self.isFailure:
            return False
        if self.valueIVC is None:
            return False

        return self.valueIVC.isVector()

    @ComputedGraph.ExposedFunction(expandArgs=True)
    def writeToS3(self, bucketname, keyname):
        """Trigger a task writing this dataset to amazon S3.

        Returns a WriteToS3Task object.
        """
        if not isinstance(bucketname, str):
            raise Exceptions.SubscribableWebObjectsException("Expected bucketname to be a string")
        if not isinstance(keyname, str):
            raise Exceptions.SubscribableWebObjectsException("Expected keyname to be a string")

        if self.valueIVC is None:
            return None

        task = WriteToS3Task.WriteToS3Task(computedValue=self, bucketname=bucketname, keyname=keyname)

        task.trigger()

        return task

class ComputedValueForMember(ComputedValue):
    baseComputedValue = object
    memberName = object

    def args(self):
        return (self.baseComputedValue, ForaNative.makeSymbol("Member"), ForaNative.makeSymbol(self.memberName))

