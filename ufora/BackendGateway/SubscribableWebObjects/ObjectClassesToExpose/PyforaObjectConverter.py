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
from ufora.BackendGateway.SubscribableWebObjects.SubscribableObject \
    import SubscribableObject, ExposedFunction

import ufora.FORA.python.ModuleDirectoryStructure as ModuleDirectoryStructure



class PyforaObjectConverter(SubscribableObject):
    def __init__(self, id, cumulus_gateway, cache_loader, _):
        super(PyforaObjectConverter, self).__init__(id, cumulus_gateway, cache_loader)
        self.objectIdToIvc_ = {}
        self.converter_ = [None]
        self.objectRegistry_ = [None]


    @ExposedFunction(expandArgs=True)
    def initialize(self, purePythonMDSAsJson):
        """Initialize the converter assuming a set of pyfora builtins"""
        try:
            import pyfora.ObjectRegistry as ObjectRegistry
            import ufora.FORA.python.PurePython.Converter as Converter
            import ufora.FORA.python.PurePython.PyforaSingletonAndExceptionConverter \
                as PyforaSingletonAndExceptionConverter
            import ufora.native.FORA as ForaNative
            import ufora.FORA.python.ModuleImporter as ModuleImporter


            logging.info("Initializing the PyforaObjectConverter")

            self.objectRegistry_[0] = ObjectRegistry.ObjectRegistry()

            if purePythonMDSAsJson is None:
                self.converter_[0] = Converter.Converter()
            else:
                purePythonModuleImplval = ModuleImporter.importModuleFromMDS(
                    ModuleDirectoryStructure.ModuleDirectoryStructure.fromJson(purePythonMDSAsJson),
                    "fora",
                    "purePython",
                    searchForFreeVariables=True
                    )

                singletonAndExceptionConverter = \
                    PyforaSingletonAndExceptionConverter.PyforaSingletonAndExceptionConverter(
                        purePythonModuleImplval
                        )

                primitiveTypeMapping = {
                    bool: purePythonModuleImplval.getObjectMember("PyBool"),
                    str: purePythonModuleImplval.getObjectMember("PyString"),
                    int: purePythonModuleImplval.getObjectMember("PyInt"),
                    float: purePythonModuleImplval.getObjectMember("PyFloat"),
                    type(None): purePythonModuleImplval.getObjectMember("PyNone"),
                    }


                nativeConstantConverter = ForaNative.PythonConstantConverter(
                    primitiveTypeMapping
                    )

                nativeListConverter = ForaNative.makePythonListConverter(
                    purePythonModuleImplval.getObjectMember("PyList")
                    )

                nativeTupleConverter = ForaNative.makePythonTupleConverter(
                    purePythonModuleImplval.getObjectMember("PyTuple")
                    )

                nativeDictConverter = ForaNative.makePythonDictConverter(
                    purePythonModuleImplval.getObjectMember("PyDict")
                    )

                foraBuiltinsImplVal = ModuleImporter.builtinModuleImplVal()

                self.converter_[0] = Converter.Converter(
                    nativeListConverter=nativeListConverter,
                    nativeTupleConverter=nativeTupleConverter,
                    nativeDictConverter=nativeDictConverter,
                    nativeConstantConverter=nativeConstantConverter,
                    singletonAndExceptionConverter=singletonAndExceptionConverter,
                    vdmOverride=self.cache_loader.vdm,
                    purePythonModuleImplVal=purePythonModuleImplval,
                    foraBuiltinsImplVal=foraBuiltinsImplVal
                    )
        except:
            logging.critical("Failed to initialize the PyforaObjectConverter: %s",
                             traceback.format_exc())
            raise


    def hasObjectId(self, objectId):
        return objectId in self.objectIdToIvc_


    def getIvcFromObjectId(self, objectId):
        return self.objectIdToIvc_[objectId]


    def unwrapPyforaDictToDictOfAssignedVars(self, dictIVC):
        """Take a Pyfora dictionary, and return a dict {string->IVC}.
           Returns None if not possible."""
        return self.converter_[0].unwrapPyforaDictToDictOfAssignedVars(dictIVC)


    def unwrapPyforaTupleToTuple(self, tupleIVC):
        """Take a Pyfora tuple, and return a tuple {IVC}.
           Returns None if not possible."""
        return self.converter_[0].unwrapPyforaTupleToTuple(tupleIVC)


    @ExposedFunction(expandArgs=True)
    def convert(self, objectId, objectIdToObjectDefinition):
        import pyfora.TypeDescription as TypeDescription
        import pyfora.Exceptions as PyforaExceptions

        result = [None]
        def onConverted(r):
            result[0] = r

        t0 = time.time()

        self.objectRegistry_[0].objectIdToObjectDefinition.update({
            int(k): TypeDescription.deserialize(v)
            for k, v in objectIdToObjectDefinition.iteritems()
            })

        logging.info("Updated object registry in %s seconds.", time.time() - t0)
        t0 = time.time()

        try:
            self.converter_[0].convert(objectId, self.objectRegistry_[0], onConverted)
        except Exception as e:
            logging.error("Converter raised an exception: %s", traceback.format_exc())
            raise Exceptions.InternalError("Unable to convert objectId %s" % objectId)

        logging.info("Converted to fora in %s seconds", time.time() - t0)

        assert result[0] is not None

        if isinstance(result[0], PyforaExceptions.PythonToForaConversionError):
            return {'isException': True, 'message': result[0].message, 'trace': result[0].trace}

        if isinstance(result[0], Exception):
            raise Exceptions.SubscribableWebObjectsException(result[0].message)

        self.objectIdToIvc_[objectId] = result[0]
        return {'objectId': objectId}


    def transformPyforaImplval(self, result, transformer, vectorContentsExtractor):
        return self.converter_[0].transformPyforaImplval(result,
                                                         transformer,
                                                         vectorContentsExtractor)
