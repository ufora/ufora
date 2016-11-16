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
import collections
import pyfora.pyAst.NodeVisitorBases as NodeVisitorBases
import pyfora.Exceptions as Exceptions
import pyfora.pyAst.PyAstUtil as PyAstUtil

VarWithPosition = collections.namedtuple('VarWithPosition', ['var', 'pos'])

class _CollectBoundValuesInScopeTransvisitor(NodeVisitorBases.GenericInScopeTransvisitor):
    """
    Collect the variables and names that are bound in the current scope.

    This visitor does not recursively descend into nested scopes.
    It separately keeps track of Names (i.e., function and class declarations) and Variables.
    """

    def __init__(self, node):
        super(_CollectBoundValuesInScopeTransvisitor, self).__init__(node)
        self._boundVarsWithPos = set()
        self._boundNamesWithPos = set()

    def getBoundNames(self):
        self._cachedCompute()
        return {var for (var, _) in self._boundNamesWithPos}

    def getBoundVariables(self):
        self._cachedCompute()
        return {var for (var, _) in self._boundVarsWithPos}

    def getBoundValues(self, getPositions=False):
        self._cachedCompute()
        if getPositions:
            return self._boundVarsWithPos.union(self._boundNamesWithPos)
        else:
            return self.getBoundVariables().union(self.getBoundNames())

    def visit_Module(self, _):
        raise Exceptions.InternalError(
            "Unexpected call of 'visit_Module' in '%s'" % self.__class__.__name__)

    def visit_FunctionDef(self, node):
        # exclude synthetic wrapper FunctionDef nodes
        if node.name != '':
            self._boundNamesWithPos.add(
                VarWithPosition(
                    var=node.name,
                    pos=NodeVisitorBases.PositionInFile(
                        lineno=node.lineno,
                        col_offset=node.col_offset
                        )
                    )
                )
        return node

    def visit_ClassDef(self, node):
        self._boundNamesWithPos.add(
            VarWithPosition(
                var=node.name,
                pos=NodeVisitorBases.PositionInFile(
                    lineno=node.lineno,
                    col_offset=node.col_offset
                    )
                )
            )
        return node

    def visit_Lambda(self, node):
        return node

    def visit_Name(self, node):
        if self._isInDefinition:
            self._boundVarsWithPos.add(
                VarWithPosition(
                    var=node.id,
                    pos=NodeVisitorBases.PositionInFile(
                        lineno=node.lineno,
                        col_offset=node.col_offset
                        )
                    )
                )
        return node

    def visit_Attribute(self, node):
        return node # do not visit sub-tree

    def visit_Global(self, node):
        raise Exceptions.PythonToForaConversionError(
            "'global' statement not supported in Python to Fora translation (line %s)."
            % node.lineno)

    def visit_arguments(self, node):
        self.visit(node.defaults)
        with self._isInDefinitionMgr(newValue=True):
            self.visit(node.args)
        if node.vararg is not None:
            self._boundVarsWithPos.add(
                VarWithPosition(
                    var=node.vararg,
                    pos=NodeVisitorBases.PositionInFile(
                        lineno=node.lineno,
                        col_offset=node.col_offset
                        )
                    )
                )
        if node.kwarg is not None:
            self._boundVarsWithPos.add(
                VarWithPosition(
                    var=node.kwarg,
                    pos=NodeVisitorBases.PositionInFile(
                        lineno=node.lineno,
                        col_offset=node.col_offset
                        )
                    )
                )
        return node


def collectBoundValuesInScope(pyAstNode, getPositions=False):
    vis = _CollectBoundValuesInScopeTransvisitor(pyAstNode)
    return vis.getBoundValues(getPositions)


def collectBoundVariablesInScope(pyAstNode):
    vis = _CollectBoundValuesInScopeTransvisitor(pyAstNode)
    return vis.getBoundVariables()


def collectBoundNamesInScope(pyAstNode):
    vis = _CollectBoundValuesInScopeTransvisitor(pyAstNode)
    return vis.getBoundNames()

class _FreeVariableMemberAccessChainsTransvisitor(NodeVisitorBases.GenericScopedTransvisitor):
    """Collect the free variable member access chains in a block of code."""
    def __init__(self, exclude_predicate=None):
        scopeMgr = NodeVisitorBases.ScopedSaveRestoreComputedValue(
            self.getBoundValues,
            self._setBoundValues,
            _FreeVariableMemberAccessChainsTransvisitor._computeScopeBoundValues)
        super(_FreeVariableMemberAccessChainsTransvisitor, self).__init__(scopeMgr)
        self._boundValues = set()
        self._boundInScopeSoFar = set()

        self._freeVariableMemberAccessChainsWithPos = set()
        self._freeVariablesWithPos = set()
        self.exclude_predicate = exclude_predicate

    def getBoundValues(self):
        return (self._boundValues, self._boundInScopeSoFar)
    def _setBoundValues(self, valueSets):
        (self._boundValues, self._boundInScopeSoFar) = valueSets
    @staticmethod
    def _computeScopeBoundValues(node, oldValueSets):
        return (oldValueSets[0].union(collectBoundValuesInScope(node)), set())
    def isBoundSoFar(self, name):
        return name in self._boundValues or name in self._boundInScopeSoFar
    def isFree(self, var):
        return any(var == free_var for (free_var, _pos) in self._freeVariablesWithPos)
    def getFreeVars(self, getPositions=False):
        if getPositions:
            return self._freeVariablesWithPos
        else:
            return {var for (var, _) in self._freeVariablesWithPos}
    def getFreeVariablesMemberAccessChains(self, getPositions=False):
        if getPositions:
            return self._freeVariableMemberAccessChainsWithPos
        else:
            return {chain for (chain, _) in self._freeVariableMemberAccessChainsWithPos}

    def addFreeVariableMemberAccessChain(self, chain, lineno, col_offset):
        pos = NodeVisitorBases.PositionInFile(
                    lineno=lineno,
                    col_offset=col_offset
                    )
        self._freeVariableMemberAccessChainsWithPos.add(
            VarWithPosition(var=chain, pos=pos))
        self._freeVariablesWithPos.add(
            VarWithPosition(var=chain[0], pos=pos))

    def processChain(self, chain, ctx, lineno, col_offset):
        '''Updates bound and free variables and returns isBoundSoFar before call.'''
        identifier = chain[0]
        if self.isBoundSoFar(identifier):
            return True
        else:
            if isinstance(ctx, ast.Store):
                self._boundInScopeSoFar.add(identifier)
            elif isinstance(ctx, ast.Load):
                self.addFreeVariableMemberAccessChain(chain, lineno, col_offset)
            return False

    def visit_Attribute(self, node, allow_recursion=True):
        (chainOrNone, root) = _memberAccessChainWithLocOrNone(node)
        if chainOrNone is not None:
            self.processChain(chainOrNone, root.ctx, root.lineno, root.col_offset)
        elif allow_recursion:
            # required to recurse deeper into the AST, but only do it if
            # _freeVariableMemberAccessChain was None, indicating that it
            # doesn't want to consume the whole expression
            self.generic_visit(node.value)
        return node

    def visit_Name(self, node):
        identifier = node.id
        self.processChain((identifier,), node.ctx, node.lineno, node.col_offset)
        return node

    def visit_ClassDef(self, node):
        self._boundValues.add(node.name)
        return NodeVisitorBases.GenericScopedTransvisitor.visit_ClassDef(self, node)

    def generic_visit(self, node):
        if self.exclude_predicate is None or not self.exclude_predicate(node):
            super(_FreeVariableMemberAccessChainsTransvisitor, self).generic_visit(node)
        return node

def getFreeVariables(pyAstNode, isClassContext=None, getPositions=False):
    pyAstNode = PyAstUtil.getRootInContext(pyAstNode, isClassContext)
    freeVarsVisitor = _FreeVariableMemberAccessChainsTransvisitor()
    freeVarsVisitor.visit(pyAstNode)
    return freeVarsVisitor.getFreeVars(getPositions=getPositions)

def getFreeVariableMemberAccessChains(pyAstNode,
                                      isClassContext=None,
                                      getPositions=False,
                                      exclude_predicate=None):
    pyAstNode = PyAstUtil.getRootInContext(pyAstNode, isClassContext)
    vis = _FreeVariableMemberAccessChainsTransvisitor(exclude_predicate)
    vis.visit(pyAstNode)
    return vis.getFreeVariablesMemberAccessChains(getPositions)


class _FreeVariableMemberAccessChainsCollapsingTransformer(_FreeVariableMemberAccessChainsTransvisitor):
    """Find free variable chains of the form x.y.z and replace them with single variable lookups"""
    def __init__(self, chain_to_new_name):
        super(_FreeVariableMemberAccessChainsCollapsingTransformer, self).__init__()
        self.chain_to_new_name = chain_to_new_name

    def visit_Attribute(self, node):
        _FreeVariableMemberAccessChainsTransvisitor.visit_Attribute(
                                                    self, node, allow_recursion=False)

        (chainOrNone, _root) = _memberAccessChainWithLocOrNone(node)

        if chainOrNone is not None:
            chain = tuple(chainOrNone)
            identifier = chain[0]
            if chain in self.chain_to_new_name and self.isFree(identifier):
                return ast.fix_missing_locations(
                            ast.copy_location(
                                ast.Name(self.chain_to_new_name[chain], node.ctx),
                                node
                                )
                            )
        return self.generic_visit(node)


def _memberAccessChainOrNone(pyAstNode):
    return _memberAccessChainWithLocOrNone(pyAstNode)[0]

def _memberAccessChainWithLocOrNone(pyAstNode):
    (chain, root) = _memberAccessChainWithLocImpl(pyAstNode)

    if len(chain) == 0:
        return (None, None)

    return (tuple(chain), root)


def _memberAccessChainWithLocImpl(pyAstNode):
    ''' Return a pair containing the access chain list and the root node.'''
    if isinstance(pyAstNode, ast.Name):
        return ([pyAstNode.id], pyAstNode)

    if isinstance(pyAstNode, ast.Expr):
        return _memberAccessChainWithLocImpl(pyAstNode.value)

    if isinstance(pyAstNode, ast.Attribute):
        # expr.attr: Attribute(expr value, identifier attr, expr_context context)
        (prefix, root) = _memberAccessChainWithLocImpl(pyAstNode.value)
        if len(prefix) == 0:
            return ([], None)  # return empty list for unexpected node-type

        prefix.append(pyAstNode.attr)
        return (prefix, root)

    return ([], None)  # return empty list for unexpected node-type


def collapseFreeVariableMemberAccessChains(pyAstNode,
                                      chain_to_name,
                                      isClassContext=None
                                      ):
    pyAstNode = PyAstUtil.getRootInContext(pyAstNode, isClassContext)
    vis = _FreeVariableMemberAccessChainsCollapsingTransformer(chain_to_name)
    return vis.visit(pyAstNode)
