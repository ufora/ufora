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
import pyfora.PyAstUtil as PyAstUtil
import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.PyObjectNodes as PyObjectNodes
import pyfora.PyforaInspect as PyforaInspect
import pyfora.PyforaWithBlock as PyforaWithBlock
import pyfora.NamedSingletons as NamedSingletons

import logging
import __builtin__
import ast


def isClassInstance(pyObject):
    return hasattr(pyObject, "__class__")


NoneType = type(None)


def _isPrimitive(pyObject):
    return isinstance(pyObject, (NoneType, int, float, str, bool))


class PyObjectWalker(object):
    """
    Generic class for walking a python object (in a way we like), and calling
    a visitor on each node.

    Instance Attributes:
      walkedNodes: dictionary of nodes walked (id -> object)
      visitor: visitor to be called on walked nodes
      purePythonClassMapping: Instance of PureImplementationMappings.PureImplementationMappings
      _convertedObjectCache: dictionary (id -> PyObjectNode?)
      _fileTextCache: dictionary (? -> ?)
    """

    def __init__(
            self,
            visitor,
            purePythonClassMapping=None
            ):
        self.walkedNodes = dict()
        self.visitor = visitor

        if purePythonClassMapping is None:
            purePythonClassMapping = PureImplementationMappings.PureImplementationMappings()
        self.purePythonClassMapping = purePythonClassMapping

        self._convertedObjectCache = dict()

        self._fileTextCache = dict()


    def resetWalkedNodes(self):
        self.walkedNodes = dict()

    def setVisitor(self, visitor):
        self.visitor = visitor

    def walkPyObject(self, pyObject):
        """Recursively walk pyObject and call visitor on it and return None.

        May choose to walk a different node instead. Populates"""

        if id(pyObject) in self.walkedNodes:
            return

        # Note: We add this to the walkedNodes dict before we possibly get an
        # alternate object to walk below.
        self.walkedNodes[id(pyObject)] = pyObject

        objectToWalkInsteadOrNone = self._objectToWalkInsteadOrNone(pyObject)
        if objectToWalkInsteadOrNone is not None:
            self.walkPyObject(objectToWalkInsteadOrNone)
            return

        self.visitor.visit(pyObject)
        
        if isinstance(pyObject, PyObjectNodes.WithBlock):
            self._walkWithBlock(pyObject)
        elif isinstance(pyObject, PyObjectNodes.List):
            self._walkList(pyObject)
        elif isinstance(pyObject, PyObjectNodes.Tuple):
            self._walkTuple(pyObject)
        elif isinstance(pyObject, PyObjectNodes.Dict):
            self._walkDict(pyObject)
        elif isinstance(pyObject, PyObjectNodes.RemotePythonObject):
            self._walkRemotePythonObject(pyObject)
        elif isinstance(pyObject, PyObjectNodes.NamedSingleton):
            self._walkNamedSingleton(pyObject)
        elif isinstance(pyObject, PyObjectNodes.BuiltinExceptionInstance):
            self._walkBuiltinExceptionInstance(pyObject)
        elif isinstance(pyObject, PyObjectNodes.ClassInstanceDescription):
            self._walkClassInstanceDescription(pyObject)
        elif isinstance(pyObject, PyObjectNodes.FunctionDefinition):
            self._walkFunctionDefinition(pyObject)
        elif isinstance(pyObject, PyObjectNodes.ClassDefinition):
            self._walkClassDefinition(pyObject)

    def unwrapConvertedObject(self, pyObject):
        if id(pyObject) in self._convertedObjectCache:
            return self._convertedObjectCache[id(pyObject)][1]
        else:
            return pyObject
        
    def _objectToWalkInsteadOrNone(self, pyObject):
        """Takes a python object and returns another python object or None.

        If the given python object belongs to the PyObjectNode hierarchy,
        return None, otherwise build or fetch from a cache the appropriate
        PyObjectNode to walk, and return it.
        """

        tr = None
        if isinstance(pyObject, PyObjectNodes.PyObjectNode):
            return tr  # If this is the common path, we may want to pull it to the call-site(s)

        if isinstance(pyObject, RemotePythonObject.RemotePythonObject):
            tr = PyObjectNodes.RemotePythonObject(pyObject)
        elif isinstance(pyObject, Exception) and pyObject.__class__ in NamedSingletons.pythonSingletonToName:
            tr = PyObjectNodes.BuiltinExceptionInstance(
                pyObject, 
                NamedSingletons.pythonSingletonToName[pyObject.__class__], 
                pyObject.args
                )
        elif isinstance(pyObject, (type, type(isinstance))) and pyObject in NamedSingletons.pythonSingletonToName:
            tr = PyObjectNodes.NamedSingleton(pyObject, NamedSingletons.pythonSingletonToName[pyObject])
        elif isinstance(pyObject, PyforaWithBlock.PyforaWithBlock):
            tr = self._pyObjectNodeForWithBlock(pyObject)
        elif id(pyObject) in self._convertedObjectCache:
            tr = self._convertedObjectCache[id(pyObject)][1]
        elif self.purePythonClassMapping.canMap(pyObject):
            pureInstance = self.purePythonClassMapping.mappableInstanceToPure(pyObject)
            self._convertedObjectCache[id(pyObject)] = (pyObject, pureInstance)
            tr = pureInstance
        elif isinstance(pyObject, tuple):
            tr = PyObjectNodes.Tuple(pyObject)
        elif isinstance(pyObject, list):
            tr = PyObjectNodes.List(pyObject)
        elif isinstance(pyObject, dict):
            tr = PyObjectNodes.Dict(pyObject)
        elif _isPrimitive(pyObject):
            tr = PyObjectNodes.Primitive(pyObject)
        elif PyforaInspect.isfunction(pyObject):
            tr = self._pyObjectNodeForFunction(pyObject)
        elif PyforaInspect.isclass(pyObject):
            tr = self._pyObjectNodeForClass(pyObject)
        elif isClassInstance(pyObject):
            tr = self._classInstanceDescriptionFromClassInstance(pyObject)

        return tr

    def _classInstanceDescriptionFromClassInstance(self, pyObject):
        classObject = pyObject.__class__

        try:
            dataMemberNames = PyAstUtil.computeDataMembers(classObject)
        except Exceptions.CantGetSourceTextError:
            self._raiseConversionErrorForSourceTextError(pyObject)
        except:
            logging.error('Failed on %s (of type %s)', pyObject, type(pyObject))
            raise
        classMemberNameToMemberValue = {}

        for dataMemberName in dataMemberNames:
            memberValue = getattr(pyObject, dataMemberName)
            classMemberNameToMemberValue[dataMemberName] = memberValue

        return PyObjectNodes.ClassInstanceDescription(
                pyObject,
                classObject,
                classMemberNameToMemberValue
                )

    def _pyObjectNodeForClass(self, pyObject):
        return self._pyObjectNodeForClassOrFunction(
            pyObject,
            classOrFunction=PyObjectNodes.ClassDefinition
            )

    def _pyObjectNodeForWithBlock(self, pyObject):
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
            self._resolveFreeVariableMemberAccesChains(
                freeVariableMemberAccessChains, pyObject.boundVariables
                )

        processedFreeVariableMemberAccessChainResolutions = { \
            '.'.join(chain): resolution for chain, resolution in \
            freeVariableMemberAccessChainResolutions.iteritems()
            }

        if pyObject.sourceFileName in self._fileTextCache:
            fileObject = self._fileTextCache[pyObject.sourceFileName]
        else:
            sourceFileText = "".join(PyforaInspect.getlines(pyObject.sourceFileName))
            fileObject = PyObjectNodes.File(pyObject.sourceFileName, sourceFileText)
            self._fileTextCache[pyObject.sourceFileName] = fileObject

        return PyObjectNodes.WithBlock(
            pyObject, 
            fileObject,
            lineNumber,
            processedFreeVariableMemberAccessChainResolutions
            )

    def _pyObjectNodeForFunction(self, pyObject):
        return self._pyObjectNodeForClassOrFunction(
            pyObject,
            classOrFunction=PyObjectNodes.FunctionDefinition
            )

    def _raiseConversionErrorForSourceTextError(self, pyObject):
        raise Exceptions.PythonToForaConversionError(
            "can't convert %s (of type %s) since we can't get its source code" % (
                pyObject, type(pyObject))
            )

    def _pyObjectNodeForClassOrFunction(self, pyObject, classOrFunction):
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

        if classOrFunction is PyObjectNodes.FunctionDefinition:
            pyAst = PyAstUtil.functionDefOrLambdaAtLineNumber(sourceAst, sourceLine)
        else:
            assert classOrFunction is PyObjectNodes.ClassDefinition
            pyAst = PyAstUtil.classDefAtLineNumber(sourceAst, sourceLine)

        freeVariableMemberAccessChainResolutions = \
            self._resolveFreeVariableMemberAccessChains(
                pyObject, pyAst
                )

        processedFreeVariableMemberAccessChainResolutions = { \
            '.'.join(chain): resolution for chain, resolution in \
            freeVariableMemberAccessChainResolutions.iteritems()
            }

        if sourceFileName in self._fileTextCache:
            fileObject = self._fileTextCache[sourceFileName]
        else:
            fileObject = PyObjectNodes.File(sourceFileName, sourceFileText)
            self._fileTextCache[sourceFileName] = fileObject
        
        return classOrFunction(
            pyObject,
            fileObject,
            sourceLine,
            processedFreeVariableMemberAccessChainResolutions
            )

    def _walkTuple(self, pyObject):
        for val in pyObject.pyObject:
            self.walkPyObject(val)

    def _walkList(self, pyObject):
        for val in pyObject.pyObject:
            self.walkPyObject(val)

    def _walkDict(self, pyObject):
        for key, val in pyObject.pyObject.iteritems():
            self.walkPyObject(key)
            self.walkPyObject(val)        

    def _walkRemotePythonObject(self, pyObject):
        pass

    def _walkNamedSingleton(self, pyObject):
        pass

    def _walkBuiltinExceptionInstance(self, pyObject):
        self.walkPyObject(pyObject.args)
            
    def _walkFunctionDefinition(self, functionDefinition):
        self._walkFunctionOrClassDefinition(functionDefinition)

    def _walkClassDefinition(self, classDefinition):
        self._walkFunctionOrClassDefinition(classDefinition)

    def _walkFunctionOrClassDefinition(self, functionOrClassDefinition):
        self.walkPyObject(functionOrClassDefinition.sourceFile)
        for _, resolution in functionOrClassDefinition\
            .freeVariableMemberAccessChainResolutions.iteritems():
            self.walkPyObject(resolution)

    def _walkWithBlock(self, withBlock):
        self.walkPyObject(withBlock.sourceFile)
        for v in withBlock.freeVariableMemberAccessChainResolutions.values():
            self.walkPyObject(v)

    def _walkClassInstanceDescription(self, classInstanceDescription):
        self.walkPyObject(classInstanceDescription.klass)
        for classMember in \
            classInstanceDescription.classMemberNameToMemberValue.values():
            self.walkPyObject(classMember)

    def _resolveFreeVariableMemberAccesChains(
            self, freeVariableMemberAccessChains, boundVariables
            ):
        resolutions = dict()

        for chain in freeVariableMemberAccessChains:
            subchain, resolution = self._resolveChainByDict(chain, boundVariables)

            if id(resolution) in self._convertedObjectCache:
                resolution = self._convertedObjectCache[id(resolution)][1]
        
            resolutions[subchain] = resolution

        return resolutions

    def _resolveFreeVariableMemberAccessChains(
            self, pyObject, pyAst
            ):

        resolutions = dict()

        freeVariableMemberAccessChains = \
            self._freeMemberAccessChains(pyAst)

        for chain in freeVariableMemberAccessChains:
            if not chain or chain[0] not in ['staticmethod']:
                subchain, resolution = self._resolveChainInPyObject(chain, pyObject)
                resolutions[subchain] = resolution

        return resolutions

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
            terminalValue = self._convertedObjectCache[id(terminalValue)][1]

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

