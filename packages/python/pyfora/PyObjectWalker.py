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


class WalkError(Exception):
    pass

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

    class UnBoundInFunctionError(Exception):
        pass

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
        elif isinstance(pyObject, type) and pyObject in NamedSingletons.pythonSingletonToName:
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
        try:
            classObject = pyObject.__class__

            dataMemberNames = PyAstUtil.computeDataMembers(classObject)
            classMemberNameToMemberValue = {}

            for dataMemberName in dataMemberNames:
                memberValue = getattr(pyObject, dataMemberName)
                classMemberNameToMemberValue[dataMemberName] = memberValue

            return PyObjectNodes.ClassInstanceDescription(
                    pyObject,
                    classObject,
                    classMemberNameToMemberValue
                    )
        except:
            logging.error('Failed on %s (of type %s)', pyObject, type(pyObject))
            raise

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

        freeVariableMemberAccessChains = \
            PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(
                withBlockFun,
                isClassContext=False
                )

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
            with open(pyObject.sourceFileName, "r") as sourceFile:
                sourceFileText = sourceFile.read()
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

    def _pyObjectNodeForClassOrFunction(self, pyObject, classOrFunction):
        try:
            sourceFileText, sourceFileName = PyAstUtil.getSourceFilenameAndText(pyObject)
        except PyAstUtil.CantGetSourceTextError as e:
            raise WalkError(e.message)

        _, sourceLine = PyforaInspect.getsourcelines(pyObject)

        sourceAst = PyAstUtil.getSourceFileAst(pyObject)

        if classOrFunction is PyObjectNodes.FunctionDefinition:
            pyAst = PyAstUtil.functionDefAtLineNumber(sourceAst, sourceLine)
        else:
            assert classOrFunction is PyObjectNodes.ClassDefinition
            pyAst = PyAstUtil.classDefAtLineNumber(sourceAst, sourceLine)

        freeVariableMemberAccessChainResolutions = \
            self._resolveFreeVariableMemberAccessChainsAndVisitUnvisited(
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
        self.walkPyObject(functionDefinition.sourceFile)

    def _walkClassDefinition(self, classDefinition):
        self.walkPyObject(classDefinition.sourceFile)

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
            subchain, resolution = self._resolveChain(chain, boundVariables)

            if id(resolution) in self._convertedObjectCache:
                resolution = self._convertedObjectCache[id(resolution)][1]
        
            resolutions[subchain] = resolution

        return resolutions

    def _resolveFreeVariableMemberAccessChainsAndVisitUnvisited(
            self, pyObject, pyAst
            ):

        # ATz: just added 'False' as a 2nd argument, but we may need to check
        # that whenever pyAst is a FunctionDef node, its context is not a class
        # (i.e., it is not an instance method). In that case, we need to pass
        # 'True' as the 2nd argument.
        freeVariableMemberAccessChains = \
            PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(pyAst, False)

        resolutions = dict()

        for chain in freeVariableMemberAccessChains:
            if not chain or chain[0] not in ['staticmethod']:
                subchain, resolution = self._resolveChainAndWalkIfNecessary(chain, pyObject)
                resolutions[subchain] = resolution

        return resolutions

    def _resolveChain(self, chain, boundVariables):
        freeVariable = chain[0]

        if freeVariable in boundVariables:
            rootValue = boundVariables[freeVariable]
            subchain, terminalValue = self._computeTerminalValueAlongModules(
                rootValue, chain
                )
            return subchain, terminalValue

        if hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

            return self._computeTerminalValueAlongModules(rootValue, chain)

        raise Exceptions.PythonToForaConversionError(
            "don't know how to resolve free variable `%s`" % freeVariable
            )

    def _resolveChainAndWalkIfNecessary(self, chain, pyObject):
        """
        This name could be improved.

        Returns a `subchain, terminalPyValue` pair: this represents the deepest value 
        we can get to in the member chain `chain` on `pyObject` taking members only
        along modules (or "empty" modules)

        """
        subchain, terminalValue = self._lookupChain(pyObject, chain)
        
        if id(terminalValue) in self._convertedObjectCache:
            terminalValue = self._convertedObjectCache[id(terminalValue)][1]
        
        idForTerminalValue = id(terminalValue)

        if idForTerminalValue not in self.walkedNodes:
            self.walkPyObject(terminalValue)

        return subchain, terminalValue

    def _lookupChain(self, pyObject, chain):
        if PyforaInspect.isfunction(pyObject):
            return self._lookupChainInFunction(pyObject, chain)

        if PyforaInspect.isclass(pyObject):
            return self._lookupChainInClass(pyObject, chain)
        
        assert False, "don't know how to lookup values in %s" % pyObject

    def _classMemberFunctions(self, pyObject):
        return PyforaInspect.getmembers(
            pyObject,
            lambda elt: PyforaInspect.ismethod(elt) or PyforaInspect.isfunction(elt)
            )

    def _lookupChainInClass(self, pyObject, chain):
        memberFunctions = self._classMemberFunctions(pyObject)

        for _, func in memberFunctions:
            try:
                # lookup should be indpendent of which function we 
                # actually choose. However, the unbound chain may not
                # appear in every member function
                return self._lookupChainInFunction(func, chain)
            except PyObjectWalker.UnBoundInFunctionError:
                pass

        assert False, "it looks like %s is free in %s" % (chain, pyObject)

    def _lookupChainInFunction(self, pyFunction, chain):
        freeVariable = chain[0]
        
        if freeVariable in pyFunction.func_code.co_freevars:
            index = pyFunction.func_code.co_freevars.index(freeVariable)
            try:
                rootValue = pyFunction.func_closure[index].cell_contents
            except:
                logging.error("Failed to get value for free variable %s", freeVariable)
                raise
            
            return self._computeTerminalValueAlongModules(rootValue, chain)

        if freeVariable in pyFunction.func_globals:
            rootValue = pyFunction.func_globals[freeVariable]

            return self._computeTerminalValueAlongModules(rootValue, chain)

        if hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

            return self._computeTerminalValueAlongModules(rootValue, chain)

        raise PyObjectWalker.UnBoundInFunctionError(
            "couldn't find a binding for var %s in pyFunction %s" % (
                freeVariable, pyFunction)
            )

    def _computeTerminalValueAlongModules(self, rootValue, chain):
        ix = 1

        subchain, terminalValue = chain[:ix], rootValue

        while PyforaInspect.ismodule(terminalValue):
            terminalValue = getattr(terminalValue, chain[ix])
            ix += 1
            subchain = chain[:ix]

        return subchain, terminalValue

