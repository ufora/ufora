#   Copyright 2016 Ufora Inc.
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

import unittest
import os
import base64
import numpy
import multiprocessing

import ufora.FORA.python.ModuleDirectoryStructure as ModuleDirectoryStructure
import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PureImplementationMapping as PureImplementationMapping
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator
import pyfora
import ufora.FORA.python.PurePython.Converter as Converter
import ufora.FORA.python.PurePython.PyforaToJsonTransformer as PyforaToJsonTransformer

class ThisIsAClass:
    def f(self):
    	return 100

def ThisIsAFunction():
    return 100

def ThisFunctionIsImpure():
    return multiprocessing.cpu_count()

class ConverterTest(unittest.TestCase):
    def test_convert_impure_function(self):
        mappings = PureImplementationMappings.PureImplementationMappings()
        registry = ObjectRegistry.ObjectRegistry()

        walker = PyObjectWalker.PyObjectWalker(
            purePythonClassMapping=mappings,
            objectRegistry=registry
            )

        objId = walker.walkPyObject(ThisFunctionIsImpure)

        for k,v in registry.objectIdToObjectDefinition.iteritems():
            if isinstance(v,str):
                v = base64.b64decode(v)
            print k, repr(v)[:200]

    
    def test_conversion_metadata(self):
        for anInstance in [ThisIsAClass(), ThisIsAFunction]:
            mappings = PureImplementationMappings.PureImplementationMappings()
            registry = ObjectRegistry.ObjectRegistry()

            walker = PyObjectWalker.PyObjectWalker(
                purePythonClassMapping=mappings,
                objectRegistry=registry
                )

            objId = walker.walkPyObject(anInstance)

            path = os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora")
            moduleTree = ModuleDirectoryStructure.ModuleDirectoryStructure.read(path, "purePython", "fora")
            converter = Converter.constructConverter(moduleTree.toJson(), None)
            anObjAsImplval = converter.convertDirectly(objId, registry)

            transformer = PyforaToJsonTransformer.PyforaToJsonTransformer()

            anObjAsJson = converter.transformPyforaImplval(
                anObjAsImplval,
                transformer,
                PyforaToJsonTransformer.ExtractVectorContents(None)
                )

            rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(mappings, allowModuleLevelLookups=False)

            convertedInstance = rehydrator.convertJsonResultToPythonObject(anObjAsJson)

            def walkJsonObject(o):
            	if isinstance(o, str):
            		try:
            			o_decoded = base64.b64decode(o)
            			return base64.b64encode(o_decoded.replace("100", "200"))
    	        	except:
    	        		return o
            	if isinstance(o, dict):
            		return {k:walkJsonObject(o[k]) for k in o}
            	if isinstance(o, tuple):
            		return tuple([walkJsonObject(x) for x in o])
            	return o

            convertedInstanceModified = rehydrator.convertJsonResultToPythonObject(walkJsonObject(anObjAsJson))

            if anInstance is ThisIsAFunction:
                self.assertEqual(anInstance(), 100)
                self.assertEqual(convertedInstance(), 100)
                self.assertEqual(convertedInstanceModified(), 200)
            else:
                self.assertEqual(anInstance.f(), 100)
                self.assertEqual(convertedInstance.f(), 100)
                self.assertEqual(convertedInstanceModified.f(), 200)

