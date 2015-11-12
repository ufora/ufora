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

import pyfora.Exceptions as Exceptions
import pyfora.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PyforaWithBlock as PyforaWithBlock
import pyfora.PyforaInspect as PyforaInspect
import pyfora.PyAstUtil as PyAstUtil

import logging
import __builtin__
import ast


def isClassInstance(pyObject):
    return hasattr(pyObject, "__class__")


NoneType = type(None)


def _isPrimitive(pyObject):
    return isinstance(pyObject, (NoneType, int, float, str, bool))


class _FunctionDefinition(object):
    def __init__(
            self,
            sourceFileId,
            lineNumber,
            freeVariableMemberAccessChainsToId
            ):
        self.sourceFileId = sourceFileId
        self.lineNumber = lineNumber
        self.freeVariableMemberAccessChainsToId = \
            freeVariableMemberAccessChainsToId


class _ClassDefinition(object):
    def __init__(
            self,
            sourceFileId,
            lineNumber,
            freeVariableMemberAccessChainsToId
            ):
        self.sourceFileId = sourceFileId
        self.lineNumber = lineNumber
        self.freeVariableMemberAccessChainsToId = \
            freeVariableMemberAccessChainsToId


class _FileDescription(object):
    _fileTextCache = {}

    def __init__(self, fileName, fileText):
        self.fileName = fileName
        self.fileText = fileText

    @classmethod
    def cachedFromArgs(cls, fileName, fileText=None):
        if fileName in cls._fileTextCache:
            return cls._fileTextCache[fileName]

        if fileText is None:
            fileText = "".join(PyforaInspect.getlines(fileName))

        tr = cls(fileName, fileText)
        cls._fileTextCache[fileName] = tr
        return tr


class PyObjectWalker(object):
    """
    `PyObjectWalker`: walk a live python object, registering its pieces with an 
    `ObjectRegistry`

    The main, and only publicly viewable function on this class is `walkPyObject`

    Attributes:
        _`purePythonClassMapping`: a `PureImplementationMapping` -- used to 
            "replace" python objects in an python object graph by a "Pure" 
            python class. For example, treat this `np.array` as a 
        `PurePython.SomePureImplementationOfNumpyArray`.
        `_convertedObjectCache`: a mapping from python id -> pure instance
        `_pyObjectIdToObjectId`: mapping from python id -> id registered in
            `self.objectRegistry`
        `_objectRegistry`: an `ObjectRegistry` which holds an image of the 
            objects we visit.
        
    """
    def __init__(self, purePythonClassMapping, objectRegistry):
        if purePythonClassMapping is None:
            purePythonClassMapping = \
                PureImplementationMappings.PureImplementationMappings()

        for singleton in NamedSingletons.pythonSingletonToName:
            if purePythonClassMapping.canMap(singleton):
                raise UserWarning(
                    "You provided a mapping that applies to %s, which already has a direct mapping" % singleton
                    )

        self._purePythonClassMapping = purePythonClassMapping
        self._convertedObjectCache = {}
        self._pyObjectIdToObjectId = {}
        self._objectRegistry = objectRegistry

    def _allocateId(self, pyObject):
        objectId = self._objectRegistry.allocateObject()
        self._pyObjectIdToObjectId[id(pyObject)] = objectId

        return objectId

    def walkPyObject(self, pyObject):
        """
        `walkPyObject`: recursively traverse a live python object, 
        registering its "pieces" with an `ObjectRegistry` 
        (`self.objectRegistry`).

        Note that we use python `id`s for caching in this class, 
        which means it cannot be used in cases where `id`s might get
        reused (recall they are just memory addresses).

        `objectId`s are assigned to all pieces of the python object.

        Returns:
            An `int`, the `objectId` of the root python object.
        """
        if id(pyObject) in self._pyObjectIdToObjectId:
            return self._pyObjectIdToObjectId[id(pyObject)]

        if id(pyObject) in self._convertedObjectCache:
            pyObject = self._convertedObjectCache[id(pyObject)]
        elif self._purePythonClassMapping.canMap(pyObject):
            pureInstance = self._purePythonClassMapping.mappableInstanceToPure(
                pyObject
                )
            self._convertedObjectCache[id(pyObject)] = pureInstance
            pyObject = pureInstance

        objectId = self._allocateId(pyObject)

        if isinstance(pyObject, RemotePythonObject.RemotePythonObject):
            self._registerRemotePythonObject(objectId, pyObject)        
        elif isinstance(pyObject, _FileDescription):
            self._registerFileDescription(objectId, pyObject)
        elif isinstance(pyObject, Exception) and pyObject.__class__ in \
           NamedSingletons.pythonSingletonToName:
            self._registerBuiltinExceptionInstance(objectId, pyObject)
        elif isinstance(pyObject, (type, type(isinstance))) and \
           pyObject in NamedSingletons.pythonSingletonToName:
            self._registerNamedSingleton(
                objectId, 
                NamedSingletons.pythonSingletonToName[pyObject]
                )
        elif isinstance(pyObject, PyforaWithBlock.PyforaWithBlock):
            self._registerWithBlock(objectId, pyObject)
        elif isinstance(pyObject, tuple):
            self._registerTuple(objectId, pyObject)
        elif isinstance(pyObject, list):
            self._registerList(objectId, pyObject)
        elif isinstance(pyObject, dict):
            self._registerDict(objectId, pyObject)
        elif _isPrimitive(pyObject):
            self._registerPrimitive(objectId, pyObject)
        elif PyforaInspect.isfunction(pyObject):
            self._registerFunction(objectId, pyObject)
        elif PyforaInspect.isclass(pyObject):
            self._registerClass(objectId, pyObject)
        elif isClassInstance(pyObject):
            self._registerClassInstance(objectId, pyObject)
        else:
            assert False, "don't know what to do with %s" % pyObject

        return objectId

    def _registerRemotePythonObject(self, objectId, remotePythonObject):
        """
        `_registerRemotePythonObject`: register a remotePythonObject
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.defineRemotePythonObject(
            objectId,
            remotePythonObject._pyforaComputedValueArg()
            )

    def _registerFileDescription(self, objectId, fileDescription):
        """
        `_registerFileDescription`: register a `_FileDescription`
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.defineFile(
            objectId=objectId,
            path=fileDescription.fileName,
            text=fileDescription.fileText
            )        

    def _registerBuiltinExceptionInstance(
            self, objectId, builtinExceptionInstance
            ):
        """
        `_registerBuiltinExceptionInstance`: register a `builtinExceptionInstance`
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the args of the instance.
        """
        argsId = self.walkPyObject(builtinExceptionInstance.args)

        self._objectRegistry.defineBuiltinExceptionInstance(
            objectId,
            NamedSingletons.pythonSingletonToName[
                builtinExceptionInstance.__class__
                ],
            argsId
            )

    def _registerNamedSingleton(self, objectId, singletonName):
        """
        `_registerNamedSingleton`: register a `NamedSingleton`
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.defineNamedSingleton(objectId, singletonName)

    def _registerTuple(self, objectId, tuple_):
        """
        `_registerTuple`: register a `tuple` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the values in the tuple.
        """
        memberIds = [self.walkPyObject(val) for val in tuple_]
        
        self._objectRegistry.defineTuple(
            objectId=objectId,
            memberIds=memberIds
            )            

    def _registerList(self, objectId, list_):
        """
        `_registerList`: register a `list` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the values in the list.
        """
        memberIds = [self.walkPyObject(val) for val in list_]
        
        self._objectRegistry.defineList(
            objectId=objectId,
            memberIds=memberIds
            )            

    def _registerPrimitive(self, objectId, primitive):
        """
        `_registerPrimitive`: register a primitive (defined by `isPrimitive`)
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.definePrimitive(
            objectId,
            primitive
            )

    def _registerDict(self, objectId, dict_):
        """
        `_registerDict`: register a `dict` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the keys and values in the dict
        """
        keyIds, valueIds = [], []
        for k, v in dict_.iteritems():
            keyIds.append(self.walkPyObject(k))
            valueIds.append(self.walkPyObject(v))
        
        self._objectRegistry.defineDict(
            objectId=objectId,
            keyIds=keyIds,
            valueIds=valueIds
            )

    def _registerClassInstance(self, objectId, classInstance):
        """
        `_registerClassInstance`: register a `class` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the class of the `classInstance`
        and on the data members of the instance.
        """
        classObject = classInstance.__class__
        classId = self.walkPyObject(classObject)

        try:
            dataMemberNames = PyAstUtil.computeDataMembers(classObject)
        except Exceptions.CantGetSourceTextError:
            self._raiseConversionErrorForSourceTextError(classInstance)
        except:
            logging.error('Failed on %s (of type %s)', classInstance, type(classInstance))
            raise
        classMemberNameToClassMemberId = {}

        for dataMemberName in dataMemberNames:
            memberId = self.walkPyObject(getattr(classInstance, dataMemberName))
            classMemberNameToClassMemberId[dataMemberName] = memberId

        self._objectRegistry.defineClassInstance(
            objectId=objectId,
            classId=classId,
            classMemberNameToClassMemberId=classMemberNameToClassMemberId
            )

    def _registerWithBlock(self, objectId, pyObject):
        """
        `_registerWithBlock`: register a `PyforaWithBlock.PyforaWithBlock`
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the resolvable free variable
        member access chains in the block and on the file object.
        """
        lineNumber = pyObject.lineNumber
        sourceTree = PyAstUtil.pyAstFromText(pyObject.sourceText)
        withBlockAst = PyAstUtil.withBlockAtLineNumber(sourceTree, lineNumber)

        withBlockFun = ast.FunctionDef(
            name="",
            args=ast.arguments(args=[], defaults=[], kwarg=None, vararg=None),
            body=withBlockAst.body,
            decorator_list=[]
            )

        if PyAstUtil.hasReturnInOuterScope(withBlockFun):
            raise Exceptions.InvalidPyforaOperation(
                "return statement not supported in pyfora with-block (line %s)" %
                PyAstUtil.getReturnLocationsInOuterScope(withBlockFun)[0])

        if PyAstUtil.hasYieldInOuterScope(withBlockFun):
            raise Exceptions.InvalidPyforaOperation(
                "yield expression not supported in pyfora with-block (line %s)" %
                PyAstUtil.getYieldLocationsInOuterScope(withBlockFun)[0])

        freeVariableMemberAccessChains = \
            self._freeMemberAccessChains(withBlockFun)

        boundValuesInScope = PyAstFreeVariableAnalyses.collectBoundValuesInScope(withBlockFun)

        for boundValue in boundValuesInScope:
            if boundValue not in pyObject.unboundLocals and boundValue in pyObject.boundVariables:
                freeVariableMemberAccessChains.add((boundValue,))

        freeVariableMemberAccessChainResolutions = \
            self._resolveFreeVariableMemberAccessChains(
                freeVariableMemberAccessChains, pyObject.boundVariables
                )

        processedFreeVariableMemberAccessChainResolutions = { \
            '.'.join(chain): self.walkPyObject(resolution) for \
            chain, resolution in freeVariableMemberAccessChainResolutions.iteritems()
            }

        sourceFileId = self.walkPyObject(
            _FileDescription.cachedFromArgs(
                fileName=pyObject.sourceFileName
                )
            )

        self._objectRegistry.defineWithBlock(
            objectId=objectId,
            freeVariableMemberAccessChainsToId=\
                processedFreeVariableMemberAccessChainResolutions,
            sourceFileId=sourceFileId,
            lineNumber=lineNumber
            )

    def _registerFunction(self, objectId, function):
        """
        `_registerFunction`: register a python function with `self.objectRegistry.

        Recursively call `walkPyObject` on the resolvable free variable member
        access chains in the function, as well as on the source file object.
        """
        functionDescription = self._classOrFunctionDefinition(
            function,
            classOrFunction=_FunctionDefinition
            )

        self._objectRegistry.defineFunction(
            objectId=objectId,
            sourceFileId=functionDescription.sourceFileId,
            lineNumber=functionDescription.lineNumber,
            scopeIds=functionDescription.freeVariableMemberAccessChainsToId
            )

    def _registerClass(self, objectId, pyObject):
        """
        `_registerClass`: register a python class with `self.objectRegistry.

        Recursively call `walkPyObject` on the resolvable free variable member
        access chains in the class, as well as on the source file object.
        """
        fileDescription = self._classOrFunctionDefinition(
            pyObject,
            classOrFunction=_ClassDefinition
            )

        self._objectRegistry.defineClass(
            objectId=objectId,
            sourceFileId=fileDescription.sourceFileId,
            lineNumber=fileDescription.lineNumber,
            scopeIds=fileDescription.freeVariableMemberAccessChainsToId
            )

    def _raiseConversionErrorForSourceTextError(self, pyObject):
        raise Exceptions.PythonToForaConversionError(
            "can't convert %s (of type %s) since we can't get its source code" % (
                pyObject, type(pyObject))
            )

    def _classOrFunctionDefinition(self, pyObject, classOrFunction):
        """
        `_classOrFunctionDefinition: create a `_FunctionDefinition` or 
        `_ClassDefinition` out of a python class or function, recursively visiting 
        the resolvable free variable member access chains in `pyObject` as well
        as the source file object.

        Args:
            `pyObject`: a python class or function.
            `classOrFunction`: should either be `_FunctionDefinition` or 
                `_ClassDefinition`.

        Returns:
            a `_FunctionDefinition` or `_ClassDefinition`.

        """
        try:
            sourceFileText, sourceFileName = PyAstUtil.getSourceFilenameAndText(pyObject)
        except Exceptions.CantGetSourceTextError:
            self._raiseConversionErrorForSourceTextError(pyObject)
        except:
            logging.error('Failed on %s (of type %s)', pyObject, type(pyObject))
            raise

        # TODO fixup: this getsourcelines call here shares a lot of the 
        # work done by getSourceFilenameAndText called previously.
        # we could DRY them up a little
        _, sourceLine = PyforaInspect.getsourcelines(pyObject)

        sourceAst = PyAstUtil.pyAstFromText(sourceFileText)

        if classOrFunction is _FunctionDefinition:
            pyAst = PyAstUtil.functionDefOrLambdaAtLineNumber(sourceAst, sourceLine)
        else:
            assert classOrFunction is _ClassDefinition
            pyAst = PyAstUtil.classDefAtLineNumber(sourceAst, sourceLine)

        freeVariableMemberAccessChainResolutions = \
            self._computeAndResolveFreeVariableMemberAccessChainsInAst(
                pyObject, pyAst
                )

        processedFreeVariableMemberAccessChainResolutions = { \
            '.'.join(chain): self.walkPyObject(resolution) for \
            chain, resolution in freeVariableMemberAccessChainResolutions.iteritems()
            }

        sourceFileId = self.walkPyObject(
            _FileDescription.cachedFromArgs(
                fileName=sourceFileName,
                fileText=sourceFileText
                )
            )
        
        return classOrFunction(
            sourceFileId=sourceFileId,
            lineNumber=sourceLine,
            freeVariableMemberAccessChainsToId=\
                processedFreeVariableMemberAccessChainResolutions
            )

    def _freeMemberAccessChains(self, pyAst):
        # ATz: just added 'False' as a 2nd argument, but we may need to check
        # that whenever pyAst is a FunctionDef node, its context is not a class
        # (i.e., it is not an instance method). In that case, we need to pass
        # 'True' as the 2nd argument.
        freeVariableMemberAccessChains = \
            PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(
                pyAst, isClassContext=False
                )

        return freeVariableMemberAccessChains

    def _resolveChainByDict(self, chain, boundVariables):
        """
        `_resolveChainByDict`: look up a free variable member access chain, `chain`,
        in a dictionary of resolutions, `boundVariables`, or in `__builtin__`.
        """
        freeVariable = chain[0]

        if freeVariable in boundVariables:
            rootValue = boundVariables[freeVariable]
            subchain, terminalValue = self._computeSubchainAndTerminalValueAlongModules(
                rootValue, chain
                )
            return subchain, terminalValue

        if hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

            return self._computeSubchainAndTerminalValueAlongModules(rootValue, chain)

        raise Exceptions.PythonToForaConversionError(
            "don't know how to resolve free variable `%s`" % freeVariable
            )

    def _resolveChainInPyObject(self, chain, pyObject):
        """
        This name could be improved.

        Returns a `subchain, terminalPyValue` pair: this represents the deepest value 
        we can get to in the member chain `chain` on `pyObject` taking members only
        along modules (or "empty" modules)

        """
        subchainAndResolutionOrNone = self._subchainAndResolutionOrNone(pyObject, chain)
        if subchainAndResolutionOrNone is None:
            raise Exceptions.PythonToForaConversionError(
                "don't know how to resolve %s in %s" % (chain, pyObject)
                )

        subchain, terminalValue = subchainAndResolutionOrNone
        
        if id(terminalValue) in self._convertedObjectCache:
            terminalValue = self._convertedObjectCache[id(terminalValue)]

        return subchain, terminalValue

    def _subchainAndResolutionOrNone(self, pyObject, chain):
        if PyforaInspect.isfunction(pyObject):
            return self._lookupChainInFunction(pyObject, chain)

        if PyforaInspect.isclass(pyObject):
            return self._lookupChainInClass(pyObject, chain)
        
        return None

    def _classMemberFunctions(self, pyObject):
        return PyforaInspect.getmembers(
            pyObject,
            lambda elt: PyforaInspect.ismethod(elt) or PyforaInspect.isfunction(elt)
            )

    def _lookupChainInClass(self, pyClass, chain):
        """
        return a pair `(subchain, subchainResolution)`
        where subchain resolves to subchainResolution in pyClass
        """
        memberFunctions = self._classMemberFunctions(pyClass)

        for _, func in memberFunctions:
            # lookup should be indpendent of which function we 
            # actually choose. However, the unbound chain may not
            # appear in every member function
                 
            subchainAndResolutionOrNone = self._lookupChainInFunction(func, chain)
            if subchainAndResolutionOrNone is not None:
                return subchainAndResolutionOrNone

        return None

    def _lookupChainInFunction(self, pyFunction, chain):
        """
        return a pair `(subchain, subchainResolution)`
        where subchain resolves to subchainResolution in pyFunction
        """
        freeVariable = chain[0]
        
        if freeVariable in pyFunction.func_code.co_freevars:
            index = pyFunction.func_code.co_freevars.index(freeVariable)
            try:
                rootValue = pyFunction.func_closure[index].cell_contents
            except:
                logging.error("Failed to get value for free variable %s", freeVariable)
                raise
            
            return self._computeSubchainAndTerminalValueAlongModules(rootValue, chain)

        if freeVariable in pyFunction.func_globals:
            rootValue = pyFunction.func_globals[freeVariable]

            return self._computeSubchainAndTerminalValueAlongModules(rootValue, chain)

        if hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

            return self._computeSubchainAndTerminalValueAlongModules(rootValue, chain)

        return None

    def _computeSubchainAndTerminalValueAlongModules(self, rootValue, chain):
        ix = 1

        subchain, terminalValue = chain[:ix], rootValue

        while PyforaInspect.ismodule(terminalValue):
            if ix >= len(chain):
                #we're terminating at a module
                raise Exceptions.PythonToForaConversionError(
                    "Can't convert the module %s" % str(terminalValue)
                    )
            
            if not hasattr(terminalValue, chain[ix]):
                raise Exceptions.PythonToForaConversionError(
                    "Module %s has no member %s" % (str(terminalValue), chain[ix])
                    )

            terminalValue = getattr(terminalValue, chain[ix])
            ix += 1
            subchain = chain[:ix]

        return subchain, terminalValue

    def _resolveFreeVariableMemberAccessChains(
            self, freeVariableMemberAccessChains, boundVariables
            ):
        resolutions = dict()

        for chain in freeVariableMemberAccessChains:
            subchain, resolution = self._resolveChainByDict(chain, boundVariables)

            if id(resolution) in self._convertedObjectCache:
                resolution = self._convertedObjectCache[id(resolution)][1]
        
            resolutions[subchain] = resolution

        return resolutions

    def _computeAndResolveFreeVariableMemberAccessChainsInAst(
            self, pyObject, pyAst
            ):
        resolutions = {}

        freeVariableMemberAccessChains = \
            self._freeMemberAccessChains(pyAst)

        for chain in freeVariableMemberAccessChains:
            if not chain or chain[0] not in ['staticmethod']:
                subchain, resolution = self._resolveChainInPyObject(chain, pyObject)
                resolutions[subchain] = resolution

        return resolutions

