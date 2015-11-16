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
import pyfora.NodeVisitorBases as NodeVisitorBases
import pyfora.PyforaInspect as PyforaInspect

import ast
import os
import textwrap


LINENO_ATTRIBUTE_NAME = 'lineno'

def CachedByArgs(f):
    """Function decorator that adds a simple memo to 'f' on its arguments"""
    cache = {}
    def inner(*args):
        if args not in cache:
            cache[args] = f(*args)
        return cache[args]
    return inner

def getSourceText(pyObject):
    try:
        source, lineno = PyforaInspect.getsourcelines(pyObject)
    except TypeError as e:
        raise Exceptions.CantGetSourceTextError(e.message)
    # Create a prefix of (lineno-1) blank lines to keep track of line numbers for error reporting
    blankLines = os.linesep * (lineno - 1)
    # We don't know how to avoid the use of `textwrap.dedent to get the code
    # though `ast.parse, which means that the computed column_numbers may be
    # off and we shouldn't report them.
    return textwrap.dedent(blankLines + "".join(source))

sourceFileCache_ = {}
def getSourceFilenameAndText(pyObject):
    try:
        sourceFile = PyforaInspect.getsourcefile(pyObject)
    except TypeError as e:
        raise Exceptions.CantGetSourceTextError(e.message)

    if sourceFile in sourceFileCache_:
        return sourceFileCache_[sourceFile], sourceFile

    sourceFileCache_[sourceFile] = "".join(PyforaInspect.getlines(sourceFile))

    return sourceFileCache_[sourceFile], sourceFile

def getSourceFileText(pyObject):
    return getSourceFilenameAndText(pyObject)[0]

@CachedByArgs
def pyAstFromText(text):
    return ast.parse(text)

def pyAstFor(pyObject):
    return pyAstFromText(getSourceText(pyObject))

def getSourceFileAst(pyObject):
    filename = PyforaInspect.getsourcefile(pyObject)
    return getAstFromFilePath(filename)

@CachedByArgs
def getAstFromFilePath(filename):
    with open(filename, "r") as f:
        return pyAstFromText(f.read())


class FindEnclosingFunctionVisitor(ast.NodeVisitor):
    """"Visitor used to find the enclosing function at a given line of code.

    The class method 'find' is the preferred API entry point."""
    def __init__(self, line):
        self.targetLine = line
        self.enclosingFunction = None
        self._currentFunction = None
        self._stash = []

    def generic_visit(self, node):
        if hasattr(node, LINENO_ATTRIBUTE_NAME):
            if node.lineno >= self.targetLine:
                self.enclosingFunction = self._currentFunction
                raise NodeVisitorBases.VisitDone
        super(FindEnclosingFunctionVisitor, self).generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.lineno > self.targetLine:
            raise NodeVisitorBases.VisitDone
        self._stash.append(self._currentFunction)
        self._currentFunction = node.name
        self.generic_visit(node)
        self._currentFunction = self._stash.pop()

    def find(self, node):
        if hasattr(node, LINENO_ATTRIBUTE_NAME):
            if node.lineno > self.targetLine:
                return None
        try:
            self.visit(node)
        except NodeVisitorBases.VisitDone:
            return self.enclosingFunction
        return None


def findEnclosingFunctionName(astNode, lineno):
    vis = FindEnclosingFunctionVisitor(lineno)
    return vis.find(astNode)

class _AtLineNumberVisitor(ast.NodeVisitor):
    """Collects various types of nodes occurring at a given line number."""
    def __init__(self, lineNumber):
        self.classDefSubnodesAtLineNumber = []
        self.withBlockSubnodesAtLineNumber = []
        self.funcDefSubnodesAtLineNumber = []
        self.lambdaSubnodesAtLineNumber = []
        self.lineNumber = lineNumber

    def visit_ClassDef(self, node):
        if node.lineno == self.lineNumber:
            self.classDefSubnodesAtLineNumber.append(node)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_With(self, node):
        if node.lineno == self.lineNumber:
            self.withBlockSubnodesAtLineNumber.append(node)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_FunctionDef(self, node):
        if node.lineno == self.lineNumber:
            self.funcDefSubnodesAtLineNumber.append(node)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Lambda(self, node):
        if node.lineno == self.lineNumber:
            self.lambdaSubnodesAtLineNumber.append(node)
        ast.NodeVisitor.generic_visit(self, node)


@CachedByArgs
def classDefAtLineNumber(sourceAst, lineNumber):
    visitor = _AtLineNumberVisitor(lineNumber)
    visitor.visit(sourceAst)

    subnodesAtLineNumber = visitor.classDefSubnodesAtLineNumber

    if len(subnodesAtLineNumber) == 0:
        raise Exceptions.CantGetSourceTextError(
            "Can't find a ClassDef at line %s." % lineNumber
            )
    if len(subnodesAtLineNumber) > 1:
        raise Exceptions.CantGetSourceTextError(
            "Can't find a unique ClassDef at line %s." % lineNumber
            )

    return subnodesAtLineNumber[0]


@CachedByArgs
def withBlockAtLineNumber(sourceAst, lineNumber):
    visitor = _AtLineNumberVisitor(lineNumber)
    visitor.visit(sourceAst)

    subnodesAtLineNumber = visitor.withBlockSubnodesAtLineNumber

    if len(subnodesAtLineNumber) == 0:
        raise Exceptions.CantGetSourceTextError(
            "can't find a WithBlock at line %s of %s" % lineNumber
            )
    if len(subnodesAtLineNumber) > 1:
        raise Exceptions.CantGetSourceTextError(
            "can't find a unique WithBlock at line %s" % lineNumber
            )

    return subnodesAtLineNumber[0]

@CachedByArgs
def functionDefOrLambdaAtLineNumber(sourceAst, lineNumber):
    visitor = _AtLineNumberVisitor(lineNumber)
    visitor.visit(sourceAst)

    subnodesAtLineNumber = visitor.funcDefSubnodesAtLineNumber + visitor.lambdaSubnodesAtLineNumber

    if len(subnodesAtLineNumber) == 0:
        raise Exceptions.CantGetSourceTextError(
            "can't find a function definition at line %s." % lineNumber
            )
    if len(subnodesAtLineNumber) > 1:
        raise Exceptions.CantGetSourceTextError(
            "can't find a unique function definition at line %s. Do you have two lambdas on the same line?" % lineNumber
            )

    return subnodesAtLineNumber[0]


def computeDataMembers(pyClassObject):
    assert PyforaInspect.isclass(pyClassObject)

    initAstOrNone = _computeInitMethodAstOrNone(pyClassObject)

    if initAstOrNone is None:
        return []

    return _computeDataMembersFromInitAst(initAstOrNone)


def _computeDataMembersFromInitAst(initAst):
    _assertOnlySimpleStatements(initAst)
    
    if len(initAst.args.args) == 0:
        raise Exceptions.PythonToForaConversionError(
            "the `__init__ method is missing a first, positional, " \
            "`self argument (line %s)."
            % (initAst.lineno)
            )

    selfArg = initAst.args.args[0]

    if not  isinstance(selfArg, ast.Name):
        raise Exceptions.InternalError(
            "the `self argument to the `__init__ method" \
            " is not of type `ast.Name (line %s)."
            % (initAst.lineno)
            )

    return _extractSimpleSelfMemberAssignments(
        initFunctionDef = initAst,
        selfName = selfArg.id
        )


def _extractSimpleSelfMemberAssignments(initFunctionDef, selfName):
    visitor = _ExtractSimpleSelfMemberAssignmentsVisitor(selfName)
    visitor.visit(initFunctionDef)
    return visitor.memberNames


class _ExtractSimpleSelfMemberAssignmentsVisitor(ast.NodeVisitor):
    def __init__(self, selfName):
        self.selfName = selfName
        self._isInAssign = False
        self.memberNames = set()

    def visit_Assign(self, node):
        savedIsInAssign = self._isInAssign
        self._isInAssign = True
        for target in node.targets:
            self.visit(target)
        self._isInAssign = savedIsInAssign

    def visit_Attribute(self, node):
        if self._isInAssign:
            if isinstance(node.value, ast.Name):
                if node.value.id == self.selfName:
                    self.memberNames.add(node.attr)


class _AssertOnlySimpleStatementsVisitor(ast.NodeVisitor):
    # should we also be raising for ast.Call nodes?
    def visit_FunctionDef(self, node):
        raise Exceptions.PythonToForaConversionError(
            "functions in `__init__ method may rebind `self argument, " \
            "so we're not allowing them (line %s)."
            % node.lineno
            )

    def visit_ClassDef(self, node):
        raise Exceptions.PythonToForaConversionError(
            "classes in `__init__ method may rebind `self argument, " \
            "so we're not allowing them (line %s)."
            % node.lineno
            )


def _assertOnlySimpleStatements(initAst):
    visitor = _AssertOnlySimpleStatementsVisitor()
    for stmt in initAst.body:
        visitor.visit(stmt)


def _computeInitMethodAstOrNone(pyClassObject):
    pyAst = pyAstFor(pyClassObject)

    assert len(pyAst.body) == 1

    classDef = pyAst.body[0]

    assert isinstance(classDef, ast.ClassDef)

    tr = None

    # recall ClassDef = (identifier name, expr* bases, stmt* body, expr* decorator_list)
    # we're taking the *last* __init__ here
    for stmt in classDef.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            tr = stmt

    return tr

def getRootInContext(pyAstNode, isClassContext):
    if not NodeVisitorBases.isScopeNode(pyAstNode):
        raise Exceptions.InternalError(
            "Unsupported type of root node in Analysis (%s)."
            % type(pyAstNode))
    if isinstance(pyAstNode, ast.FunctionDef):
        if isClassContext is None:
            raise Exceptions.InternalError(
                "Value for `isClassContext is required when `type(pyAstNode) is `ast.FunctionDef.")
        elif isClassContext is False:
            pyAstNode = ast.Module([pyAstNode])
        # else nothing
    return pyAstNode


class _OuterScopeCountingVisitor(NodeVisitorBases.GenericInScopeVisitor):
    """Scan the current scope and count various types of statements and expressions"""
    def __init__(self, root):
        super(_OuterScopeCountingVisitor, self).__init__(root)
        self._returnCount = 0
        self._yieldCount = 0
        self._returnLocs = []
        self._yieldLocs = []
    def getHasReturn(self):
        self._cachedCompute()
        return self._returnCount > 0
    def getReturnCount(self):
        self._cachedCompute()
        return self._returnCount
    def getReturnLocs(self):
        self._cachedCompute()
        return self._returnLocs
    def getHasYield(self):
        self._cachedCompute()
        return self._yieldCount > 0
    def getYieldCount(self):
        self._cachedCompute()
        return self._yieldCount
    def getYieldLocs(self):
        self._cachedCompute()
        return self._yieldLocs

    def visit_Return(self, node):
        self._returnCount += 1
        self._returnLocs.append(node.lineno)

    def visit_Yield(self, node):
        self._yieldCount += 1
        self._yieldLocs.append(node.lineno)


@CachedByArgs
def _outerScopeContingVisitorFactory(node):
    return _OuterScopeCountingVisitor(node)

def countReturnsInOuterScope(node):
    vis = _outerScopeContingVisitorFactory(node)
    return vis.getReturnCount()

def countYieldsInOuterScope(node):
    vis = _outerScopeContingVisitorFactory(node)
    return vis.getYieldCount()

def hasReturnInOuterScope(node):
    vis = _outerScopeContingVisitorFactory(node)
    return vis.getHasReturn()

def hasYieldInOuterScope(node):
    vis = _outerScopeContingVisitorFactory(node)
    return vis.getHasYield()

def hasReturnOrYieldInOuterScope(node):
    vis = _outerScopeContingVisitorFactory(node)
    return vis.getHasReturn() or vis.getHasYield()

def getReturnLocationsInOuterScope(node):
    vis = _outerScopeContingVisitorFactory(node)
    return vis.getReturnLocs()

def getYieldLocationsInOuterScope(node):
    vis = _outerScopeContingVisitorFactory(node)
    return vis.getYieldLocs()

