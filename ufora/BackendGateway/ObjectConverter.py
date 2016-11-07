#   Copyright 2015-2016 Ufora Inc.
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
import ufora.FORA.python.ModuleDirectoryStructure as MDS


class ObjectConverter(object):
    def __init__(self, vdm):
        self.vdm = vdm
        self.converter = None
        self.object_registry = None
        self.converted_objects = {}

    def initialize(self, pure_python_mds_as_json):
        """Initialize the converter assuming a set of pyfora builtins"""
        try:
            import pyfora.ObjectRegistry as ObjectRegistry
            import ufora.FORA.python.PurePython.Converter as Converter
            import ufora.FORA.python.PurePython.PyforaSingletonAndExceptionConverter \
                as PyforaSingletonAndExceptionConverter
            import ufora.native.FORA as ForaNative
            import ufora.FORA.python.ModuleImporter as ModuleImporter


            logging.info("Initializing the ObjectConverter")

            self.object_registry = ObjectRegistry.ObjectRegistry()

            if pure_python_mds_as_json is None:
                self.converter = Converter.Converter()
            else:
                purePythonModuleImplval = ModuleImporter.importModuleFromMDS(
                    MDS.ModuleDirectoryStructure.fromJson(pure_python_mds_as_json),
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

                self.converter = Converter.Converter(
                    nativeListConverter=nativeListConverter,
                    nativeTupleConverter=nativeTupleConverter,
                    nativeDictConverter=nativeDictConverter,
                    nativeConstantConverter=nativeConstantConverter,
                    singletonAndExceptionConverter=singletonAndExceptionConverter,
                    vdmOverride=self.vdm,
                    purePythonModuleImplVal=purePythonModuleImplval,
                    foraBuiltinsImplVal=foraBuiltinsImplVal
                    )
        except:
            logging.critical("Failed to initialize the ObjectConverter: %s",
                             traceback.format_exc())
            raise


    def convert(self, object_id, object_id_to_object_definition):
        import pyfora.TypeDescription as TypeDescription
        import pyfora.Exceptions as PyforaExceptions

        result = [None]
        def onConverted(r):
            result[0] = r

        t0 = time.time()

        self.object_registry.objectIdToObjectDefinition.update({
            int(k): TypeDescription.deserialize(v)
            for k, v in object_id_to_object_definition.iteritems()
            })

        logging.info("Updated object registry in %s seconds.", time.time() - t0)
        t0 = time.time()

        try:
            self.converter.convert(object_id, self.object_registry, onConverted)
        except:
            logging.error("Converter raised an exception: %s", traceback.format_exc())
            raise Exceptions.InternalError("Unable to convert objectId %s" % object_id)

        logging.info("Converted to fora in %s seconds", time.time() - t0)

        assert result[0] is not None

        if isinstance(result[0], PyforaExceptions.PythonToForaConversionError):
            return {'isException': True, 'message': result[0].message, 'trace': result[0].trace}

        if isinstance(result[0], Exception):
            raise Exceptions.SubscribableWebObjectsException(result[0].message)

        self.converted_objects[object_id] = result[0]
        return {'objectId': object_id}


    def transformPyforaImplval(self, result, transformer, vector_contents_extractor):
        return self.converter.transformPyforaImplval(result,
                                                     transformer,
                                                     vector_contents_extractor)
