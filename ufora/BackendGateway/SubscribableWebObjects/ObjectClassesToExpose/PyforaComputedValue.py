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

import logging
import traceback

import ufora.FORA.python.ForaValue as ForaValue
import ufora.BackendGateway.ComputedValue.ComputedValue as ComputedValue
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.FORA.python.PurePython.PyforaToJsonTransformer as PyforaToJsonTransformer
import ufora.BackendGateway.SubscribableWebObjects.ObjectClassesToExpose.PyforaObjectConverter \
    as PyforaObjectConverter
import ufora.native.FORA as ForaNative
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import base64

def validateObjectIds(ids):
    converter = PyforaObjectConverter.PyforaObjectConverter()
    return all([converter.hasObjectId(i) for i in ids if isinstance(i, int)])

class PyforaComputedValue(ComputedValue.ComputedValue):
    argIds = ComputedGraph.Key(object, default=None, validator=validateObjectIds)

    def args(self):
        converter = PyforaObjectConverter.PyforaObjectConverter()
        def unwrapArg(argId):
            if isinstance(argId, int):
                return converter.getIvcFromObjectId(argId)
            else:
                return argId

        implVals = tuple(unwrapArg(arg) for arg in self.argIds)

        return implVals[:1] + (ForaValue.FORAValue.symbol_Call.implVal_,) + implVals[1:]

    def __str__(self):
        return "PyforaComputedValue" + str(tuple(self.argIds))

    def pyforaDictToDictOfAssignedVarsToProxyValues(self):
        if self.valueIVC is None:
            return None

        assert not self.isException, "We should not allow exceptions to be thrown here. Instead we should " +\
            " be wrapping the code in try/catch and returning data that contains any updated variables after the exception."

        result = PyforaObjectConverter.PyforaObjectConverter()\
                    .unwrapPyforaDictToDictOfAssignedVars(self.valueIVC)
        assert isinstance(result, dict)
        return result

    @ComputedGraph.ExposedProperty()
    def pyforaDictToAssignedVarsToComputedValues(self):
        if self.isException:
            return self.jsonValueRepresentation

        stringDictToIVC = self.pyforaDictToDictOfAssignedVarsToProxyValues

        if stringDictToIVC is None:
            return None

        return {
            'isException': False,
            'dictOfProxies':  {k: PyforaDictionaryElement(baseCV=self, keyname=k) for k in stringDictToIVC}
            }

    def pyforaTupleToTuple(self):
        if self.valueIVC is None:
            return None

        result = PyforaObjectConverter.PyforaObjectConverter().unwrapPyforaTupleToTuple(self.valueIVC)
        assert isinstance(result, tuple)
        return result

    @ComputedGraph.ExposedProperty()
    def pyforaTupleToTupleOfComputedValues(self):
        if self.isException:
            return self.jsonValueRepresentation

        tupleIVC = self.pyforaTupleToTuple

        if tupleIVC is None:
            return None

        return {
            'isException': False,
            'tupleOfComputedValues': tuple([PyforaTupleElement(baseCV=self, index=ix) for ix in range(len(tupleIVC))])
            }

    @ComputedGraph.ExposedProperty()
    def jsonStatusRepresentation(self):
        """Indicate the current status of the computation.

        States:
            None - the computation is unfinished
            {'status': 'failure', 'message': message} - the computation failed for some unhandleable reason
            {'status': 'exception'} - the computation produced an exception
            {'status': 'result'} - the computation produced a result
        """
        if self.isFailure:
            message = None

            # Extracts the ErrorState object, defined in ufora/FORA/Core/ErrorState
            failure = self.result.asFailure.error
            if failure.isHalt():
                message = "Computation halted: %s" % failure.asHalt.uuid
            elif failure.isIllegalComputationState():
                message = str(failure.asIllegalComputationState.m0)
            elif failure.isMemoryQuotaExceeded():
                memoryQuotaFailure = failure.asMemoryQuotaExceeded
                message = "Memory quota exceeded (amount: %s, required: %s)" % \
                        (memoryQuotaFailure.amount, memoryQuotaFailure.required)

            return {'status': 'failure', 'message': message}

        if self.valueIVC is None:
            return None

        if self.isException:
            return {'status': 'exception'}
        else:
            return {'status': 'result'}

    @ComputedGraph.ExposedProperty()
    def jsonValueRepresentation(self):
        return PyforaResultAsJson(computedValue=self, maxBytecount=None).getResultAsJson()

    def exceptionValueAsString(self):
        if not self.isException:
            return None

        if self.valueIVC.isTuple():
            exception, stacktraceAndVarsInScope = self.valueIVC.getTuple()
            return self.unwrapExceptionIVC(exception)
        else:
            return self.unwrapExceptionIVC(self.valueIVC)

    @ComputedGraph.Function
    def unwrapExceptionIVC(self, exceptionIVC):
        try:
            return str(ForaValue.FORAValue(exceptionIVC))
        except:
            logging.error("calling 'str' on %s failed: %s", exceptionIVC, traceback.format_exc())
            return "<unknown exception>"

    def exceptionCodeLocationsAsJson(self):
        if self.valueIVC.isTuple():
            tup = self.valueIVC.getTuple()
            if len(tup) != 2:
                return None

            _, stacktrace = self.valueIVC.getTuple()
            hashes = stacktrace.getStackTrace()

            if hashes is None:
                return None

            codeLocations = [ForaNative.getCodeLocation(h) for h in hashes]

            def formatCodeLocation(c):
                if c is None:
                    return None
                if not c.defPoint.isExternal():
                    return None
                def posToJson(simpleParsePosition):
                    return {
                        'characterOffset': simpleParsePosition.rawOffset,
                        'line': simpleParsePosition.line,
                        'col': simpleParsePosition.col
                        }
                return {
                    'path': list(c.defPoint.asExternal.paths),
                    'range': {
                        'start': posToJson(c.range.start),
                        'stop': posToJson(c.range.stop)
                        }
                    }

            # return [x for x in [formatCodeLocation(c) for c in codeLocations] if x is not None]
            return [x for x in [formatCodeLocation(c) for c in codeLocations if c is not None] if x is not None]


        else:
            return None

def isOfSimpleType(implVal):
    """Is this type simple enough that when we encode a value in a numpy array using a dtype,
    we'll get back an object of the correct type?"""
    typename = str(implVal.type)

    if typename.startswith("purePython.PyInt.<instance>"):
        return True
    if typename.startswith("purePython.PyFloat.<instance>"):
        return True
    if typename.startswith("purePython.PyBool.<instance>"):
        return True
    if typename.startswith("purePython.PyNone.<instance>"):
        return True
    if typename.startswith("purePython.PyTuple.<instance>"):
        for elt in implVal.getObjectMember("@m").getTuple():
            if not isOfSimpleType(elt):
                return False
        return True
    return False


class PyforaResultAsJson(ComputedGraph.Location):
    #the value to extract
    computedValue = object

    #the maximum number of bytes we'll permit, or None
    #note that this isn't a perfect calculation, since we're going to encode as json. We assume a
    #fixed byte overhead for every object because of the json encoding
    maxBytecount = object

    @ComputedGraph.ExposedProperty()
    def resultIsPopulated(self):
        return self.getResultAsJson() is not None

    @ComputedGraph.ExposedFunction()
    def getResultAsJson(self, *args):
        """If we are over the complexity limit, None, else the result encoded as json"""
        if self.computedValue.isFailure:
            return None

        if self.computedValue.valueIVC is None:
            return None

        value = self.computedValue.valueIVC

        if self.computedValue.isException:
            if value.isTuple():
                #the first element is the exception. The second element is the stacktrace and variables.
                value = value[0]

        c = PyforaObjectConverter.PyforaObjectConverter()

        try:
            def extractVectorContents(vectorIVC):
                if len(vectorIVC) == 0:
                    return {'listContents': []}

                #if this is an unpaged vector we can handle it without callback
                vdm = ComputedValueGateway.getGateway().vdm
                if vdm.vectorDataIsLoaded(vectorIVC, 0, len(vectorIVC)) and vectorIVC.isVectorEntirelyUnpaged():
                    #see if it's a string. This is the only way to be holding a Vector of char
                    if vectorIVC.isVectorOfChar():
                        res = vdm.extractVectorContentsAsNumpyArray(vectorIVC, 0, len(vectorIVC))
                        assert res is not None
                        return {'string': res.tostring()}

                    #see if it's simple enough to transmit as numpy data
                    if len(vectorIVC.getVectorElementsJOR()) == 1 and len(vectorIVC) > 1:
                        firstElement = vdm.extractVectorItem(vectorIVC, 0)

                        if isOfSimpleType(firstElement):
                            res = vdm.extractVectorContentsAsNumpyArray(vectorIVC, 0, len(vectorIVC))

                            if res is not None:
                                assert len(res) == len(vectorIVC)
                                return {'contentsAsNumpyArray': res}

                    #see if we can extract the data as a regular pythonlist
                    res = vdm.extractVectorContentsAsPythonArray(vectorIVC, 0, len(vectorIVC)) 
                    assert res is not None
                    return {'listContents': res}

                vec = ComputedValue.ComputedValueVector(vectorImplVal=vectorIVC)
                vecSlice = vec.entireSlice

                res = None
                preventPythonArrayExtraction = False

                #see if it's a string. This is the only way to be holding a Vector of char
                if vectorIVC.isVectorOfChar():
                    res = vecSlice.extractVectorDataAsNumpyArray()
                    if res is not None:
                        res = {'string': res.tostring()}

                #see if it's simple enough to transmit as numpy data
                if res is None and len(vectorIVC.getVectorElementsJOR()) == 1 and len(vectorIVC) > 1:
                    res = vecSlice.extractVectorDataAsNumpyArray()

                    if res is not None:
                        firstElement = vecSlice.extractVectorItemAsIVC(0)
                        if firstElement is None:
                            #note we can't import this at the top of the file because this file gets imported
                            #during the build process, which doesn't have pyfora installed.
                            import pyfora.Exceptions as Exceptions
                            raise Exceptions.ForaToPythonConversionError(
                                "Shouldn't be possible to download data as numpy, and then not get the first value"
                                )

                        if isOfSimpleType(firstElement):
                            res = {'contentsAsNumpyArray': res}
                        else:
                            res = None
                    else:
                        if not vecSlice.vdmThinksIsLoaded():
                            #there's a race condition where the data could be loaded between now and
                            #the call to 'extractVectorDataAsPythonArray'. This prevents it.
                            preventPythonArrayExtraction = True

                #see if we can extract the data as a regular pythonlist
                if not preventPythonArrayExtraction and res is None:
                    res = vecSlice.extractVectorDataAsPythonArray()
                    if res is not None:
                        res = {'listContents': res}

                if res is None:
                    vecSlice.increaseRequestCount()
                    return None

                return res

            try:
                import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
                stream = BinaryObjectRegistry.BinaryObjectRegistry()

                root_id, needsLoading = c.transformPyforaImplval(
                    value,
                    stream,
                    extractVectorContents,
                    self.maxBytecount
                    )

                if needsLoading:
                    return None

                result_to_send = {'data': base64.b64encode(stream.str()), 'root_id': root_id}

            except Exception as e:
                import pyfora
                if self.computedValue.isException and isinstance(e, pyfora.ForaToPythonConversionError):
                    return {
                        'result': {
                            "untranslatableException": str(ForaValue.FORAValue(self.computedValue.valueIVC))
                            },
                        'isException': True,
                        'trace': self.computedValue.exceptionCodeLocationsAsJson
                        }
                elif isinstance(e, pyfora.ForaToPythonConversionError):
                    return {
                        'foraToPythonConversionError': e.message
                        }
                else:
                    raise

            if self.computedValue.isException:
                return {
                    'result': result_to_send,
                    'isException': True,
                    'trace': self.computedValue.exceptionCodeLocationsAsJson
                    }
            else:
                return {
                    'result': result_to_send,
                    'isException': False
                    }

        except PyforaToJsonTransformer.HaltTransformationException:
            if self.computedValue.isException:
                return {
                    'maxBytesExceeded': True,
                    'isException': True,
                    'trace': self.computedValue.exceptionCodeLocationsAsJson
                    }
            else:
                return {'maxBytesExceeded': True, 'isException': False}


class PyforaDictionaryElement(PyforaComputedValue):
    #the base PyforaComputedValue of which we are one of the dictionary members
    baseCV = ComputedGraph.Key(object)

    #the keyname in self.baseCV.pyforaDictToStringDict we are tied to
    keyname = ComputedGraph.Key(object)

    def argIds(self):
        return ()

    def args(self):
        return (self.baseCV,
                ForaNative.makeSymbol("RawGetItemByString"),
                ForaNative.ImplValContainer(self.keyname))

    def __str__(self):
        return "PyforaDictionaryElement(baseCV=%s,keyname=%s)" % (self.baseCV, self.keyname)

class PyforaTupleElement(PyforaComputedValue):
    #the base PyforaComputedValue of which we are one of the tuple members
    baseCV = ComputedGraph.Key(object)

    #the index in self.baseCV.pyforaTupleToTuple we are tied to
    index = ComputedGraph.Key(object)

    def argIds(self):
        return ()

    def args(self):
        return (self.baseCV,
                ForaNative.makeSymbol("RawGetItemByInt"),
                ForaNative.ImplValContainer(self.index))

    def __str__(self):
        return "PyforaTupleElement(baseCV=%s,index=%s)" % (self.baseCV, self.index)

