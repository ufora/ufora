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

import pyfora.pyAst.PyAstUtil as PyAstUtil
import pyfora.PyforaInspect as PyforaInspect
import pyfora.Exceptions as Exceptions
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PyAbortSingletons as PyAbortSingletons
import pyfora.ModuleLevelObjectIndex as ModuleLevelObjectIndex
import pyfora.pyAst.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import cPickle as pickle
import sys
import os
import ast
import traceback
import logging
import base64
import numpy
import cPickle


def sanitizeModulePath(pathToModule):
    res = os.path.abspath(pathToModule)
    if res.endswith(".pyc"):
        res = res[:-1]
    return res


@PyAstUtil.CachedByArgs
def updatePyAstMemberChains(pyAst, variablesInScope, isClassContext):
    #in the variables we've been handed, every member access chain 'x.y.z' has been
    #replaced with an actual variable lookup of the form 'x.y.z'. We need to perform
    #this same replacement in the actual python source code we're running, since
    #we may not actually have enough information to recover 'x'

    replacements = {}
    for possible_replacement in variablesInScope:
        if '.' in possible_replacement:
            replacements[tuple(possible_replacement.split('.'))] = possible_replacement

    #we need to deepcopy the AST since the collapser modifies the AST, and this is just a 
    #slice of a cached tree.
    pyAst = pickle.loads(pickle.dumps(pyAst))

    pyAst = PyAstFreeVariableAnalyses.collapseFreeVariableMemberAccessChains(pyAst, replacements, isClassContext=isClassContext)

    ast.fix_missing_locations(pyAst)

    return pyAst

class PythonObjectRehydrator(object):
    """PythonObjectRehydrator - responsible for building local copies of objects
                                produced by the server."""
    def __init__(self, purePythonClassMapping, allowModuleLevelLookups=True):
        self.allowModuleLevelLookups = allowModuleLevelLookups
        self.moduleClassesAndFunctionsByPath = {}
        self.pathsToModules = {}
        self.purePythonClassMapping = purePythonClassMapping
        self.loadPathsToModules()

    def loadPathsToModules(self):
        for module in list(sys.modules.itervalues()):
            if module is not None:
                if hasattr(module, '__file__'):
                    self.pathsToModules[sanitizeModulePath(module.__file__)] = module


    def moduleLevelObject(self, path, lineNumber):
        if not self.allowModuleLevelLookups:
            return None

        if path not in self.moduleClassesAndFunctionsByPath:
            self.populateModuleMembers(path)

        if lineNumber in self.moduleClassesAndFunctionsByPath[path]:
            return self.moduleClassesAndFunctionsByPath[path][lineNumber]
 
        return None

    def populateModuleMembers(self, path):
        res = {}
        module = self.moduleForFile(path)

        if module is not None:
            for leafItemName in module.__dict__:
                leafItemValue = module.__dict__[leafItemName]

                if PyforaInspect.isclass(leafItemValue) or PyforaInspect.isfunction(leafItemValue):
                    try:
                        sourcePath = PyforaInspect.getsourcefile(leafItemValue)

                        if os.path.samefile(path, sourcePath):
                            _, lineNumber = PyforaInspect.findsource(leafItemValue)

                            lineNumberToUse = lineNumber + 1

                            if lineNumberToUse in res:
                                raise Exceptions.ForaToPythonConversionError(
                                    ("PythonObjectRehydrator got a line number collision at lineNumber %s"
                                     ", between %s and %s"),
                                    lineNumberToUse,
                                    leafItemValue,
                                    res[lineNumber + 1]
                                    )


                            res[lineNumberToUse] = leafItemValue
                        else:
                            self.populateModuleMembers(sourcePath)
                        
                    except Exceptions.ForaToPythonConversionError:
                        raise
                    except Exception as e:
                        logging.critical("PyforaInspect threw an exception: %s. tb = %s",
                                         e,
                                         traceback.format_exc())

        self.moduleClassesAndFunctionsByPath[path] = res

    def moduleForFile(self, path):
        path = sanitizeModulePath(path)
        
        if path not in self.pathsToModules:
            self.loadPathsToModules()

        return self.pathsToModules.get(path)

    def importModuleMagicVariables(self, targetDict, path):
        """Find the module at 'path' and set 'targetDict' to have the same magic
           vars (e.g. module path etc.)"""
        actualModule = self.moduleForFile(path)
        if actualModule is not None:
            for magicVar in ['__file__', '__path__', '__name__', '__package__']:
                if hasattr(actualModule, magicVar):
                    targetDict[magicVar] = getattr(actualModule, magicVar)


    def convertJsonResultToPythonObject(self, json):
        root_id = json['root_id']
        definitions = json['obj_definitions']
        converted = {}

        def convert(objectId):
            if objectId in converted:
                return converted[objectId]
            converted[objectId] = convertInner(definitions[objectId])
            return converted[objectId]

        def convertInner(objectDef):
            if 'primitive' in objectDef:
                res = objectDef['primitive']
                if isinstance(res, str):
                    return intern(str(base64.b64decode(res)))
                else:
                    return res

            if 'tuple' in objectDef:
                return tuple([convert(x) for x in objectDef['tuple']])
            if 'list' in objectDef:
                return [convert(x) for x in objectDef['list']]
            if 'dict' in objectDef:
                return {
                    convert(key): convert(val)
                    for key, val in zip(objectDef['dict']['keys'], objectDef['dict']['values'])
                    }
            if 'untranslatableException' in objectDef:
                return Exceptions.ForaToPythonConversionError(
                    "untranslatable FORA exception: %s" % objectDef['untranslatableException']
                    )
            if 'singleton' in objectDef:
                singletonName = objectDef['singleton']
                return NamedSingletons.singletonNameToObject[singletonName]
            if 'InvalidPyforaOperation' in objectDef:
                return Exceptions.InvalidPyforaOperation(objectDef['InvalidPyforaOperation'])
            if 'homogenousListNumpyDataStringsAndSizes' in objectDef:
                stringsAndSizes = objectDef['homogenousListNumpyDataStringsAndSizes']

                dtype = cPickle.loads(base64.b64decode(objectDef['dtype']))
                data = numpy.zeros(shape=objectDef['length'], dtype=dtype)

                curOffset = 0
                for dataAndSize in stringsAndSizes:
                    arrayText = dataAndSize['data']
                    size = dataAndSize['length']
                    data[curOffset:curOffset+size] = numpy.ndarray(shape=size,
                                                                   dtype=dtype,
                                                                   buffer=base64.b64decode(arrayText))
                    curOffset += size

                #we use the first element as a prototype when decoding
                firstElement = convert(objectDef['firstElement'])

                data = data.tolist()
                assert isinstance(data[0], type(firstElement)), "%s of type %s is not %s" % (
                    data[0], type(data[0]), type(firstElement)
                    )
                return data

            if 'builtinException' in objectDef:
                builtinExceptionTypeName = objectDef['builtinException']
                builtinExceptionType = NamedSingletons.singletonNameToObject[builtinExceptionTypeName]
                args = convert(objectDef['args'])
                return builtinExceptionType(*args)
            if 'classInstance' in objectDef:
                members = {
                    k: convert(v)
                    for k, v in objectDef['members'].iteritems()
                    }
                classObject = convert(objectDef['classInstance'])
                return self._invertPureClassInstanceIfNecessary(
                    self._instantiateClass(classObject, members)
                    )
            if 'pyAbortException' in objectDef:
                pyAbortExceptionTypeName = objectDef['pyAbortException']
                pyAbortExceptionType = PyAbortSingletons.singletonNameToObject[
                    pyAbortExceptionTypeName]
                args = convert(objectDef['args'])
                return pyAbortExceptionType(*args)
            if 'boundMethodOn' in objectDef:
                instance = convert(objectDef['boundMethodOn'])
                try:
                    return getattr(instance, objectDef['methodName'])
                except AttributeError:
                    raise Exceptions.ForaToPythonConversionError(
                        "Expected %s to have a method of name %s which it didn't" % (
                            instance,
                            objectDef['methodName'])
                        )
            if 'moduleLevelObject' in objectDef:
                return ModuleLevelObjectIndex.ModuleLevelObjectIndex.singleton().getObjectFromPath(objectDef['moduleLevelObject'])

            if 'functionInstance' in objectDef:
                members = {
                    k: convert(v)
                    for k, v in objectDef['members'].iteritems()
                    }
                return self._instantiateFunction(objectDef['functionInstance'][0],
                                                 objectDef['functionInstance'][1],
                                                 members,
                                                 convert(objectDef['file_text'])
                                                 )
            if 'withBlock' in objectDef:
                members = {
                    k: convert(v)
                    for k, v in objectDef['members'].iteritems()
                    }
                return self._withBlockAsClassObjectFromFilenameAndLine(objectDef['classObject'][0],
                                                            objectDef['classObject'][1],
                                                            members,
                                                            convert(objectDef['file_text'])
                                                            )

            if 'classObject' in objectDef:
                members = {
                    k: convert(v)
                    for k, v in objectDef['members'].iteritems()
                    }
                return self._classObjectFromFilenameAndLine(objectDef['classObject'][0],
                                                            objectDef['classObject'][1],
                                                            members,
                                                            convert(objectDef['file_text'])
                                                            )
            if 'stacktrace' in objectDef:
                return objectDef['stacktrace']

            raise Exceptions.ForaToPythonConversionError(
                "not implemented: cant convert %s" % objectDef
                )

        return convert(root_id)

    def _invertPureClassInstanceIfNecessary(self, instance):
        if self.purePythonClassMapping.canInvert(instance):
            return self.purePythonClassMapping.pureInstanceToMappable(instance)
        return instance

    def _withBlockAsClassObjectFromFilenameAndLine(self, filename, lineNumber, members, fileText):
        """Construct a class object given its textual definition."""
        assert fileText is not None

        sourceAst = PyAstUtil.pyAstFromText(fileText)
        withBlockAst = PyAstUtil.withBlockAtLineNumber(sourceAst, lineNumber)

        outputLocals = {}
        globalScope = {}
        globalScope.update(members)

        self.importModuleMagicVariables(globalScope, filename)

        try:
            moduleAst = updatePyAstMemberChains(ast.Module([classAst]), tuple(globalScope.keys()), isClassContext=False)

            code = compile(moduleAst, filename, 'exec')

            exec code in globalScope, outputLocals
        except:
            logging.error("Failed to instantiate class at %s:%s\n%s",
                          filename,
                          lineNumber,
                          traceback.format_exc())
            raise Exceptions.PyforaError(
                "Failed to instantiate class at %s:%s" % (filename, lineNumber)
                )

        assert len(outputLocals) == 1

        return list(outputLocals.values())[0]


    def _classObjectFromFilenameAndLine(self, filename, lineNumber, members, fileText):
        """Construct a class object given its textual definition."""
        assert fileText is not None

        objectOrNone = self.moduleLevelObject(filename, lineNumber)
        
        if objectOrNone is not None:
            return objectOrNone

        sourceAst = PyAstUtil.pyAstFromText(fileText)
        classAst = PyAstUtil.classDefAtLineNumber(sourceAst, lineNumber)

        outputLocals = {}
        globalScope = {}
        globalScope.update(members)

        self.importModuleMagicVariables(globalScope, filename)

        try:
            moduleAst = updatePyAstMemberChains(ast.Module([classAst]), tuple(globalScope.keys()), isClassContext=False)

            code = compile(moduleAst, filename, 'exec')

            exec code in globalScope, outputLocals
        except:
            logging.error("Failed to instantiate class at %s:%s\n%s",
                          filename,
                          lineNumber,
                          traceback.format_exc())
            raise Exceptions.PyforaError(
                "Failed to instantiate class at %s:%s" % (filename, lineNumber)
                )

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


    def _instantiateFunction(self, filename, lineNumber, memberDictionary, file_text):
        """Instantiate a function instance."""
        objectOrNone = self.moduleLevelObject(filename, lineNumber)
        if objectOrNone is not None:
            return objectOrNone

        sourceAst = PyAstUtil.pyAstFromText(file_text)
        functionAst = PyAstUtil.functionDefOrLambdaOrWithBlockAtLineNumber(sourceAst, lineNumber)

        outputLocals = {}
        globalScope = {}
        globalScope.update(memberDictionary)
        self.importModuleMagicVariables(globalScope, filename)

        if isinstance(functionAst, ast.Lambda):
            expr = ast.FunctionDef()
            expr.name = '__pyfora_lambda_builder__'
            expr.args = ast.arguments()
            expr.args.args = []
            expr.args.defaults = []
            expr.args.vararg = None
            expr.args.kwarg = None

            expr.decorator_list = []
            expr.lineno = functionAst.lineno-1
            expr.col_offset = functionAst.col_offset

            return_statement = ast.Return(functionAst)
            expr.body = [return_statement]

            expr = updatePyAstMemberChains(ast.Module([expr], lineno=1,col_offset=0), tuple(globalScope.keys()), isClassContext=True)

            code = compile(expr, filename, 'exec')

            exec code in globalScope, outputLocals

            return list(outputLocals.values())[0]()

        elif isinstance(functionAst, ast.With):
            expr = ast.FunctionDef()
            expr.name = '__pyfora_with_block_as_function__'
            expr.args = ast.arguments()
            expr.args.args = []
            expr.args.defaults = []
            expr.args.vararg = None
            expr.args.kwarg = None

            expr.decorator_list = []
            expr.body = functionAst.body
            expr.lineno = functionAst.lineno-1
            expr.col_offset = functionAst.col_offset

            free_variables = PyAstFreeVariableAnalyses.getFreeVariables(expr, isClassContext=True)
            bound_variables = PyAstFreeVariableAnalyses.collectBoundValuesInScope(expr)

            return_statement = ast.Return(
                    ast.Tuple([
                        ast.Dict(
                            keys=[ast.Str(x,lineno=1,col_offset=0) for x in bound_variables],
                            values=[ast.Name(x, ast.Load(), lineno=1,col_offset=1) for x in bound_variables],
                            lineno=1,
                            col_offset=0
                            ),
                        ast.Num(0,lineno=1,col_offset=0),
                        ast.Num(0,lineno=1,col_offset=0)
                        ],
                    ast.Load(),
                    lineno=1,
                    col_offset=0
                    ),
                lineno=1,
                col_offset=0
                )

            expr.body.append(return_statement)

            #for every incoming variable 'x' that's also assigned to, create a dummy '__pyfora_var_guard_x' that actually
            #takes the value in from the surrounding scope, and immediately assign it
            for var in memberDictionary:
                if var in bound_variables:
                    newVar = "__pyfora_var_guard_" + var

                    var_copy_expr = ast.Assign(
                        targets=[ast.Name(var, ast.Store(),lineno=0,col_offset=0)],
                        value=ast.Name(newVar, ast.Load(),lineno=1,col_offset=0),
                        lineno=1,
                        col_offset=0
                        )

                    globalScope[newVar] = globalScope[var]
                    del globalScope[var]

                    expr.body = [var_copy_expr] + expr.body

            expr = updatePyAstMemberChains(expr, tuple(globalScope.keys()), isClassContext=True)

            code = compile(ast.Module([expr]), filename, 'exec')

            exec code in globalScope, outputLocals
            assert len(outputLocals) == 1
            return list(outputLocals.values())[0]
        else:
            functionAst = updatePyAstMemberChains(ast.Module([functionAst], lineno=1,col_offset=0), tuple(globalScope.keys()), isClassContext=False)

            code = compile(functionAst, filename, 'exec')

            exec code in globalScope, outputLocals
            assert len(outputLocals) == 1
            return list(outputLocals.values())[0]
