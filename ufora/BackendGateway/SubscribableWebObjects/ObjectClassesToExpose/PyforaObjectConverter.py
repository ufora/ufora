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
import time
import traceback

import ufora.BackendGateway.SubscribableWebObjects.Exceptions as Exceptions
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.FORA.python.ModuleDirectoryStructure as ModuleDirectoryStructure

#global variables to hold the state of the converter. This is OK because
#the PyforaObjectConverter is a singleton
objectIdToIvc_ = {}
converter_ = [None]
objectRegistry_ = [None]

class PyforaObjectConverter(ComputedGraph.Location):
    @ComputedGraph.ExposedFunction(expandArgs=True)
    def initialize(self, purePythonMDSAsJson):
        """Initialize the converter assuming a set of pyfora builtins"""
        import pyfora.ObjectRegistry as ObjectRegistry
        import ufora.FORA.python.PurePython.Converter as Converter

        try:
            logging.info("Initializing the PyforaObjectConverter")

            objectRegistry_[0] = ObjectRegistry.ObjectRegistry()

            converter_[0] = Converter.constructConverter(purePythonMDSAsJson, ComputedValueGateway.getGateway().vdm)
        except:
            logging.critical("Failed to initialize the PyforaObjectConverter: %s", traceback.format_exc())
            raise

    @ComputedGraph.Function
    def hasObjectId(self, objectId):
        return objectId in objectIdToIvc_

    @ComputedGraph.Function
    def getIvcFromObjectId(self, objectId):
        return objectIdToIvc_[objectId]

    @ComputedGraph.Function
    def unwrapPyforaDictToDictOfAssignedVars(self, dictIVC):
        """Take a Pyfora dictionary, and return a dict {string->IVC}. Returns None if not possible."""
        return converter_[0].unwrapPyforaDictToDictOfAssignedVars(dictIVC)

    @ComputedGraph.Function
    def unwrapPyforaTupleToTuple(self, tupleIVC):
        """Take a Pyfora tuple, and return a tuple {IVC}. Returns None if not possible."""
        return converter_[0].unwrapPyforaTupleToTuple(tupleIVC)

    @ComputedGraph.ExposedFunction(expandArgs=True)
    def convert(self, objectId, objectIdToObjectDefinition):
        import pyfora.TypeDescription as TypeDescription
        import pyfora.Exceptions as PyforaExceptions

        result = [None]
        def onConverted(r):
            result[0] = r

        t0 = time.time()

        objectRegistry_[0].objectIdToObjectDefinition.update({
            int(k): TypeDescription.deserialize(v)
            for k, v in objectIdToObjectDefinition.iteritems()
            })

        logging.info("Updated object registry in %s seconds.", time.time() - t0)
        t0 = time.time()

        try:
            converter_[0].convert(objectId, objectRegistry_[0], onConverted)
        except Exception as e:
            logging.error("Converter raised an exception: %s", traceback.format_exc())
            raise Exceptions.InternalError("Unable to convert objectId %s" % objectId)

        logging.info("Converted to fora in %s seconds", time.time() - t0)

        assert result[0] is not None

        if isinstance(result[0], PyforaExceptions.PythonToForaConversionError):
            return {'isException': True, 'message': result[0].message, 'trace': result[0].trace}

        if isinstance(result[0], Exception):
            raise Exceptions.SubscribableWebObjectsException(result[0].message)

        objectIdToIvc_[objectId] = result[0]
        return {'objectId': objectId}

    @ComputedGraph.Function
    def transformPyforaImplval(self, result, transformer, vectorContentsExtractor):
        return converter_[0].transformPyforaImplval(result, transformer, vectorContentsExtractor)


