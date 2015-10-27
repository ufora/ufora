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

import pyfora.PyforaInspect as PyforaInspect
import pyfora.Exceptions as Exceptions

import ast
import os
import textwrap

def CachedByArgs(f):
    """Function decorator that adds a simple memo to 'f' on its arguments"""
    cache = {}
    def inner(*args):
        if args in cache:
            return cache[args]
        cache[args] = f(*args)
        return cache[args]
    return inner

def getSourceText(pyObject):
    try:
        source, lineno = PyforaInspect.getsourcelines(pyObject)
    except TypeError as e:
        raise Exceptions.CantGetSourceTextError(e.message)
    # Create a prefix of lineno-1 blank lines so we can keep track of line
    # numbers for error reporting
    blankLines = ""
    for _ in xrange(1, lineno):
        blankLines += os.linesep
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
    with open(sourceFile, "r") as f:
        tr = f.read()
    sourceFileCache_[sourceFile] = tr

    return tr, sourceFile

def getSourceFileText(pyObject):
    return getSourceFilenameAndText(pyObject)[0]

@CachedByArgs
def pyAstFromText(text):
    return ast.parse(text)

def getSourceFileAst(pyObject):
    filename = PyforaInspect.getsourcefile(pyObject)
    return getAstFromFilePath(filename)

@CachedByArgs
def getAstFromFilePath(filename):
    with open(filename, "r") as f:
        return pyAstFromText(f.read())

class _ClassDefsAtLineNumberVisitor(ast.NodeVisitor):
    def __init__(self, lineNumber):
        self.subnodesAtLineNumber = []
        self.lineNumber = lineNumber

    def visit_ClassDef(self, node):
        if node.lineno == self.lineNumber:
            self.subnodesAtLineNumber.append(node)
        ast.NodeVisitor.generic_visit(self, node)

@CachedByArgs
def classDefAtLineNumber(sourceAst, lineNumber):
    visitor = _ClassDefsAtLineNumberVisitor(lineNumber)
    visitor.visit(sourceAst)

    subnodesAtLineNumber = visitor.subnodesAtLineNumber

    if len(subnodesAtLineNumber) == 0:
        raise Exceptions.CantGetSourceTextError(
            "Can't find a ClassDef at line %s." % lineNumber
            )
    if len(subnodesAtLineNumber) > 1:
        raise Exceptions.CantGetSourceTextError(
            "Can't find a unique ClassDef at line %s." % lineNumber
            )

    return subnodesAtLineNumber[0]

class _WithBlockAtLineNumberVisitor(ast.NodeVisitor):
    def __init__(self, lineNumber):
        self.lineNumber = lineNumber
        self.subnodesAtLineNumber = []
    
    def visit_With(self, node):
        if node.lineno == self.lineNumber:
            self.subnodesAtLineNumber.append(node)
        ast.NodeVisitor.generic_visit(self, node)


@CachedByArgs
def withBlockAtLineNumber(sourceAst, lineNumber):
    visitor = _WithBlockAtLineNumberVisitor(lineNumber)
    visitor.visit(sourceAst)

    subnodesAtLineNumber = visitor.subnodesAtLineNumber

    if len(subnodesAtLineNumber) == 0:
        raise CantGetSourceTextError(
            "can't find a WithBlock at line %s" % lineNumber
            )
    if len(subnodesAtLineNumber) > 1:
        raise CantGetSourceTextError(
            "can't find a unique WithBlock at line %s" % lineNumber
            )

    return subnodesAtLineNumber[0]

class _FunctionDefsAtLineNumberVisitor(ast.NodeVisitor):
    def __init__(self, lineNumber):
        self.subnodesAtLineNumber = []
        self.lineNumber = lineNumber

    def visit_FunctionDef(self, node):
        if node.lineno == self.lineNumber:
            self.subnodesAtLineNumber.append(node)
        ast.NodeVisitor.generic_visit(self, node)


@CachedByArgs
def functionDefAtLineNumber(sourceAst, lineNumber):
    visitor = _FunctionDefsAtLineNumberVisitor(lineNumber)
    visitor.visit(sourceAst)

    subnodesAtLineNumber = visitor.subnodesAtLineNumber

    if len(subnodesAtLineNumber) == 0:
        raise Exceptions.CantGetSourceTextError(
            "can't find a FunctionDef at line %s." % lineNumber
            )
    if len(subnodesAtLineNumber) > 1:
        raise Exceptions.CantGetSourceTextError(
            "can't find a unique FunctionDef at line %s." % lineNumber
            )

    return subnodesAtLineNumber[0]

def pyAstFor(pyObject):
    return pyAstFromText(getSourceText(pyObject))
 
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

def isScopeNode(pyAstNode):
    if isinstance(pyAstNode, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.Lambda)):
        return True
    else:
        return False

def getRootInContext(pyAstNode, isClassContext):
    if not isScopeNode(pyAstNode):
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


