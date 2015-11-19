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

import pyfora.PyAstUtil as PyAstUtil
import pyfora.PyforaInspect as PyforaInspect
import pyfora.Exceptions as Exceptions
import pyfora.NamedSingletons as NamedSingletons
import sys
import os
import ast
import traceback
import logging
import base64
import numpy

moduleType = type(os)
builtins = sys.modules['__builtin__']

def sanitizeModulePath(pathToModule):
    res = os.path.abspath(pathToModule)
    if res.endswith(".pyc"):
        res = res[:-1]
    return res

class PythonObjectRehydrator:
    """PythonObjectRehydrator - responsible for building local copies of objects produced by the server."""
    def __init__(self, purePythonClassMapping):
        self.moduleClassesAndFunctionsByPath = {}
        self.pathsToModules = {}
        self.purePythonClassMapping = purePythonClassMapping

        for moduleName, module in list(sys.modules.iteritems()):
            if module is not None:
                if hasattr(module, '__file__'):
                    self.pathsToModules[sanitizeModulePath(module.__file__)] = module


    def moduleLevelObject(self, path, lineNumber):
        if path not in self.moduleClassesAndFunctionsByPath:
            self.populateModuleMembers(path)

        if lineNumber in self.moduleClassesAndFunctionsByPath[path]:
            return self.moduleClassesAndFunctionsByPath[path][lineNumber]
        return None

    def populateModuleMembers(self, path):
        res = {}
        module = self.moduleForFile(path)

        for leafItemName in module.__dict__:
            leafItemValue = module.__dict__[leafItemName]

            if PyforaInspect.isclass(leafItemValue) or PyforaInspect.isfunction(leafItemValue):
                try:
                    _, lineNumber = PyforaInspect.findsource(leafItemValue)
                    res[lineNumber+1] = leafItemValue
                except:
                    pass

        self.moduleClassesAndFunctionsByPath[path] = res


    def moduleForFile(self, path):
        path = sanitizeModulePath(path)
        if path in self.pathsToModules:
            return self.pathsToModules[path]

    def importModuleMagicVariables(self, targetDict, path):
        """Find the module at 'path' and set 'targetDict' to have the same magic vars (e.g. module path etc.)"""
        actualModule = self.moduleForFile(path)
        if actualModule is not None:
            for magicVar in ['__file__', '__path__', '__name__', '__package__']:
                if hasattr(actualModule, magicVar):
                    targetDict[magicVar] = getattr(actualModule, magicVar)


    def convertJsonResultToPythonObject(self, jsonResult):
        if 'primitive' in jsonResult:
            res = jsonResult['primitive']
            if isinstance(res, unicode):
                return intern(str(res))
            else:
                return res

        if 'tuple' in jsonResult:
            return tuple([self.convertJsonResultToPythonObject(x) for x in jsonResult['tuple']])
        if 'list' in jsonResult:
            return [self.convertJsonResultToPythonObject(x) for x in jsonResult['list']]
        if 'dict' in jsonResult:
            return {
                self.convertJsonResultToPythonObject(key): self.convertJsonResultToPythonObject(val) \
                for key, val in zip(jsonResult['dict']['keys'], jsonResult['dict']['values'])
                }
        if 'untranslatableException' in jsonResult:
            return Exceptions.ForaToPythonConversionError(
                "untranslatable FORA exception: %s" % jsonResult['untranslatableException']
                )
        if 'singleton' in jsonResult:
            singletonName = jsonResult['singleton']
            return NamedSingletons.singletonNameToObject[singletonName]
        if 'InvalidPyforaOperation' in jsonResult:
            return Exceptions.InvalidPyforaOperation(jsonResult['InvalidPyforaOperation'])
        if 'homogenousListNumpyDataStringsAndSizes' in jsonResult:
            stringsAndSizes = jsonResult['homogenousListNumpyDataStringsAndSizes']

            data = numpy.zeros(shape=jsonResult['length'], dtype=jsonResult['dtype'])

            curOffset = 0
            for dataAndSize in stringsAndSizes:
                arrayText = dataAndSize['data']
                size = dataAndSize['length']
                data[curOffset:curOffset+size] = numpy.ndarray(shape=size,dtype=jsonResult['dtype'], buffer=base64.b64decode(arrayText))

            #we use the first element as a prototype when decoding
            firstElement = self.convertJsonResultToPythonObject(jsonResult['firstElement'])

            data = data.tolist()
            assert isinstance(data[0], type(firstElement)), "%s of type %s is not %s" % (data[0], type(data[0]), type(firstElement))
            return data

        if 'builtinException' in jsonResult:
            builtinExceptionTypeName = jsonResult['builtinException']
            builtinExceptionType = NamedSingletons.singletonNameToObject[builtinExceptionTypeName]
            args = self.convertJsonResultToPythonObject(jsonResult['args'])
            return builtinExceptionType(*args)
        if 'classInstance' in jsonResult:
            members = {k:self.convertJsonResultToPythonObject(v) for k,v in jsonResult['members'].iteritems()}
            classObject = self.convertJsonResultToPythonObject(jsonResult['classInstance'])
            return self._invertPureClassInstanceIfNecessary(self._instantiateClass(classObject, members))
        if 'boundMethodOn' in jsonResult:
            instance = self.convertJsonResultToPythonObject(jsonResult['boundMethodOn'])
            try:
                return getattr(instance, jsonResult['methodName'])
            except AttributeError:
                raise Exceptions.ForaToPythonConversionError(
                    "Expected %s to have a method of name %s which it didn't" % 
                        (instance, jsonResult['methodName'])
                    )
        if 'functionInstance' in jsonResult:
            members = {k:self.convertJsonResultToPythonObject(v) for k,v in jsonResult['members'].iteritems()}
            return self._instantiateFunction(jsonResult['functionInstance'][0], jsonResult['functionInstance'][1], members)
        if 'classObject' in jsonResult:
            members = {k:self.convertJsonResultToPythonObject(v) for k,v in jsonResult['members'].iteritems()}
            return self._classObjectFromFilenameAndLine(jsonResult['classObject'][0], jsonResult['classObject'][1], members)
        if 'stacktrace' in jsonResult:
            return jsonResult['stacktrace']
        
        raise Exceptions.ForaToPythonConversionError("not implemented: cant convert %s" % jsonResult)

    def _invertPureClassInstanceIfNecessary(self, instance):
        if self.purePythonClassMapping.canInvert(instance):
            return self.purePythonClassMapping.pureInstanceToMappable(instance)
        return instance

    def _classObjectFromFilenameAndLine(self, filename, lineNumber, members):
        """Construct a class object given its textual definition."""
        objectOrNone = self.moduleLevelObject(filename, lineNumber)
        if objectOrNone is not None:
            return objectOrNone

        sourceAst = PyAstUtil.getAstFromFilePath(filename)
        classAst = PyAstUtil.classDefAtLineNumber(sourceAst, lineNumber)

        outputLocals = {}
        globalScope = {}
        globalScope.update(members)

        self.importModuleMagicVariables(globalScope, filename)

        try:
            code = compile(ast.Module([classAst]), filename, 'exec')

            exec code in globalScope, outputLocals
        except:
            logging.error("Failed to instantiate class at %s:%s\n%s", filename, lineNumber, traceback.format_exc())
            raise Exceptions.PyforaError("Failed to instantiate class at %s:%s" % (filename, lineNumber))

        assert len(outputLocals) == 1

        return list(outputLocals.values())[0]
        

    def _instantiateClass(self, classObject, memberDictionary):
        """Instantiate a class given its defined methods."""
        if '__init__' in dir(classObject):
            origInit = classObject.__init__
            def alteredInit(self, **kwds):
                self.__dict__.update(kwds)
            classObject.__init__ = alteredInit

            res = classObject(**memberDictionary)

            classObject.__init__ = origInit
        else:
            assert len(memberDictionary) == 0
            return classObject()

        return res

    def _instantiateFunction(self, filename, lineNumber, memberDictionary):
        """Instantiate a function instance."""
        objectOrNone = self.moduleLevelObject(filename, lineNumber)
        if objectOrNone is not None:
            return objectOrNone

        sourceAst = PyAstUtil.getAstFromFilePath(filename)
        functionAst = PyAstUtil.functionDefOrLambdaAtLineNumber(sourceAst, lineNumber)

        outputLocals = {}
        globalScope = {}
        globalScope.update(memberDictionary)
        self.importModuleMagicVariables(globalScope, filename)

        if isinstance(functionAst, ast.Lambda):
            expr = ast.Expression()
            expr.body = functionAst
            expr.lineno = functionAst.lineno
            expr.col_offset = functionAst.col_offset

            code = compile(expr, filename, 'eval')

            return eval(code, globalScope, outputLocals)
        else:
            code = compile(ast.Module([functionAst]), filename, 'exec')

            exec code in globalScope, outputLocals

            assert len(outputLocals) == 1

            return list(outputLocals.values())[0]
            

