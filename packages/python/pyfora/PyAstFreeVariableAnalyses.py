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

"""Provide some basic analyses for Python code that we want to convert to Fora.

This module exports the following functions:
getFreeVariables(astNode, isClassContext = None):
    returns a set of strings listing the identifiers of the variables that
    are free in the subtree defined by `pyAstNode. Currently, only three
    types of ast nodes are supported: ast.Module, ast.FunctionDef, and
    ast.ClassDef. The second argument to the funtion (`isClassContext) is
    needed when we pass it an ast.FunctionDef because its enclosing context
    affects the results of the analysis.

getFreeVariableMemberAccessChains(astNode, isClassContext = None):
    like `getFreeVariables above but returns member-access-chains instead of
    simple names.

collectBoundValuesInScope(astNode):
    returns a set of strings with the names and variables that are bound in
    a scope, without recursively descending into nested scopes.

collectBoundVariablesInScope(astNode):
    same as `collectBoundValuesInScope, but only returns variables.

collectBoundNamesInScope(astNode)
    same as `collectBoundValuesInScope, but only returns names (i.e.,
    function or class declarations) .
"""
import ast
import pyfora.NodeVisitorBases as NodeVisitorBases
import pyfora.Exceptions as Exceptions
import pyfora.PyAstUtil as PyAstUtil

class _CollectBoundValuesInScopeVisitor(NodeVisitorBases.GenericInScopeVisitor):
    """
    Collect the variables and names that are bound in the current scope.

    This visitor does not recursively descend into nested scopes.
    It separately keeps track of Names (i.e., function and class declarations) and Variables.
    """

    def __init__(self, node):
        super(_CollectBoundValuesInScopeVisitor, self).__init__(node)
        self._boundVars = set()
        self._boundNames = set()

    def getBoundNames(self):
        self._cachedCompute()
        return self._boundNames

    def getBoundVariables(self):
        self._cachedCompute()
        return self._boundVars

    def getBoundValues(self):
        self._cachedCompute()
        return self._boundVars.union(self._boundNames)

    def visit_Module(self, _):
        raise Exceptions.InternalError(
            "Unexpected call of 'visit_Module' in '%s'" % self.__class__.__name__)

    def visit_FunctionDef(self, node):
        self._boundNames.add(node.name)


    def visit_ClassDef(self, node):
        self._boundNames.add(node.name)

    def visit_Lambda(self, _):
        return

    def visit_Name(self, node):
        if self._isInDefinition:
            self._boundVars.add(node.id)

    def visit_Attribute(self, _):
        return  # do not visit sub-tree

    def visit_Global(self, node):
        raise Exceptions.PythonToForaConversionError(
            "'global' statement not supported in Python to Fora translation (line %s)."
            % node.lineno)

    def visit_arguments(self, node):
        self.visit(node.defaults)
        with self._isInDefinitionMgr(True):
            self.visit(node.args)
        if node.vararg is not None:
            self._boundVars.add(node.vararg)
        if node.kwarg is not None:
            self._boundVars.add(node.kwarg)


def collectBoundValuesInScope(pyAstNode):
    vis = _CollectBoundValuesInScopeVisitor(pyAstNode)
    return vis.getBoundValues()


def collectBoundVariablesInScope(pyAstNode):
    vis = _CollectBoundValuesInScopeVisitor(pyAstNode)
    return vis.getBoundVariables()


def collectBoundNamesInScope(pyAstNode):
    vis = _CollectBoundValuesInScopeVisitor(pyAstNode)
    return vis.getBoundNames()


class GenericBoundValuesScopedVisitor(NodeVisitorBases.GenericScopedVisitor):
    """Extending GenericScopedVisitor by specializing the context manager to track bound values."""
    def __init__(self):
        scopeMgr = NodeVisitorBases.ScopedSaveRestoreComputedValue(
            self.getBoundValues,
            self._setBoundValues,
            GenericBoundValuesScopedVisitor._computeScopeBoundValues)
        super(GenericBoundValuesScopedVisitor, self).__init__(scopeMgr)
        self._boundValues = set()
        self._boundInScopeSoFar = set()

    def getBoundValues(self):
        return (self._boundValues, self._boundInScopeSoFar)
    def _setBoundValues(self, valueSets):
        (self._boundValues, self._boundInScopeSoFar) = valueSets
    @staticmethod
    def _computeScopeBoundValues(node, oldValueSets):
        return (oldValueSets[0].union(collectBoundValuesInScope(node)), set())
    def isBoundSoFar(self, name):
        return name in self._boundValues or name in self._boundInScopeSoFar

    def visit_ClassDef(self, node):
        self._boundValues.add(node.name)
        NodeVisitorBases.GenericScopedVisitor.visit_ClassDef(self, node)

class _FreeVarsVisitor(GenericBoundValuesScopedVisitor):
    """Collect the free variables in a block of code."""
    def __init__(self):
        super(_FreeVarsVisitor, self).__init__()
        self._freeVars = set()

    def getFreeVars(self):
        return self._freeVars

    # VISITORS
    def visit_Name(self, node):
        identifier = node.id
        if isinstance(node.ctx, ast.Store):
            self._boundInScopeSoFar.update(identifier)
        elif not self.isBoundSoFar(identifier) and \
           isinstance(node.ctx, ast.Load):
            self._freeVars.add(identifier)


def getFreeVariables(pyAstNode, isClassContext = None):
    pyAstNode = PyAstUtil.getRootInContext(pyAstNode, isClassContext)
    freeVarsVisitor = _FreeVarsVisitor()
    freeVarsVisitor.visit(pyAstNode)
    return freeVarsVisitor.getFreeVars()


class _FreeVariableMemberAccessChainsVisitor(GenericBoundValuesScopedVisitor):
    """Collect the free variable member access chains in a block of code."""
    def __init__(self):
        super(_FreeVariableMemberAccessChainsVisitor, self).__init__()
        self.freeVariableMemberAccessChains = set()

    def visit_Attribute(self, node):
        chainOrNone = _freeVariableMemberAccessChain(node)
        if chainOrNone is not None:
            if chainOrNone[0] not in self._boundValues:
                self.freeVariableMemberAccessChains.add(chainOrNone)
        else:
            #required to recurse deeper into the AST, but only do it if
            #_freeVariableMemberAccessChain was None, indicating that it
            #doesn't want to consume the whole expression
            self.generic_visit(node.value)

    def visit_Name(self, node):
        identifier = node.id
        if isinstance(node.ctx, ast.Store):
            self._boundInScopeSoFar.update(identifier)
        elif not self.isBoundSoFar(identifier) and \
           isinstance(node.ctx, ast.Load):
            self.freeVariableMemberAccessChains.add((identifier,))


def _freeVariableMemberAccessChain(pyAstNode):
    res = _freeVariableMemberAccessChainImpl(pyAstNode)

    if len(res) == 0:
        return None

    return tuple(res)


def _freeVariableMemberAccessChainImpl(pyAstNode):
    if isinstance(pyAstNode, ast.Name):
        return [pyAstNode.id]

    if isinstance(pyAstNode, ast.Expr):
        return _freeVariableMemberAccessChainImpl(pyAstNode.value)

    if isinstance(pyAstNode, ast.Attribute):
        # Attribute(expr value, identifier attr, expr_context context)
        prefix = _freeVariableMemberAccessChainImpl(pyAstNode.value)
        if len(prefix) == 0:
            return []  # how can this path be exercised?

        prefix.append(pyAstNode.attr)
        return prefix

    return []  # how can this path be exercised?


def getFreeVariableMemberAccessChains(pyAstNode, isClassContext=None):
    pyAstNode = PyAstUtil.getRootInContext(pyAstNode, isClassContext)
    freeVariableMemberAccessChainsVisitor = _FreeVariableMemberAccessChainsVisitor()
    freeVariableMemberAccessChainsVisitor.visit(pyAstNode)

    return freeVariableMemberAccessChainsVisitor.freeVariableMemberAccessChains

