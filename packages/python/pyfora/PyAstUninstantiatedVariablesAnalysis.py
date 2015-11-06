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

import pyfora.NodeVisitorBases as NodeVisitorBases
import pyfora.Exceptions as Exceptions
import pyfora.PyAstUtil as PyAstUtil
import pyfora.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses

def collectPossiblyUninitializedLocalVariablesInScope(pyAstNode):
    boundVariables = PyAstFreeVariableAnalyses.collectBoundVariablesInScope(pyAstNode)
    visitor = _PossiblyUninitializedLocalVariablesInScopeVisitor(
        pyAstNode,
        boundVariables)
    possiblyUninitializedVariables = visitor.getPossiblyUninitializedLocalVariablesInScope()
    return possiblyUninitializedVariables

class _PossiblyUninitializedLocalVariablesInScopeVisitor(NodeVisitorBases.GenericInScopeVisitor):
    """Collect possibly uninitialized local variables in current scope"""
    def __init__(self, root, localVars):
        super(_PossiblyUninitializedLocalVariablesInScopeVisitor, self).__init__(root)
        self._localVars = localVars
        self._definitelyInitialized = set()
        self._possiblyUninitialized = set()
        self._setsStash = []

    def _pushSaveSets(self):
        self._setsStash.append((self._possiblyUninitialized.copy(),
                                self._definitelyInitialized.copy()))
    def _popRestoreSets(self):
        (self._possiblyUninitialized, self._definitelyInitialized) = \
            self._setsStash.pop()

    def _peekRestoreSets(self):
        self._possiblyUninitialized = self._setsStash[len(self._setsStash) - 1][0].copy()
        self._definitelyInitialized = self._setsStash[len(self._setsStash) - 1][1].copy()

    def getPossiblyUninitializedLocalVariablesInScope(self):
        self._cachedCompute()
        return self._possiblyUninitialized

    def visit_Name(self, node):
        identifier = node.id
        if self._isInDefinition:
            self._definitelyInitialized.add(identifier)
        elif identifier in self._localVars and \
            identifier not in self._definitelyInitialized:
            self._possiblyUninitialized.add(identifier)

    def _visitBodyOrelse(self, node):
        self._pushSaveSets()

        self.visit(node.body)
        savedAfterIfMustBeInit = self._definitelyInitialized
        savedAfterIfMayBeUninit = self._possiblyUninitialized

        self._popRestoreSets()
        self.visit(node.orelse)

        self._definitelyInitialized.intersection_update(savedAfterIfMustBeInit)
        self._possiblyUninitialized.update(savedAfterIfMayBeUninit)

    def visit_AugAssign(self, node):
        self.generic_visit(node)  # override base class method

    # If(expr test, stmt* body, stmt* orelse)
    def visit_If(self, node):
        self.visit(node.test)
        self._visitBodyOrelse(node)

    def visit_For(self, node):
        self._pushSaveSets()
        with self._isInDefinitionMgr():
            self.visit(node.target)
        self.visit(node.iter)
        self.visit(node.body)
        savedAfterForMayBeUninit = self._possiblyUninitialized

        self._peekRestoreSets()
        self.visit(node.orelse)
        savedAfterElseMayBeUninit = self._possiblyUninitialized

        self._popRestoreSets()
        self._possiblyUninitialized.update(savedAfterForMayBeUninit)
        self._possiblyUninitialized.update(savedAfterElseMayBeUninit)

    def visit_While(self, node):
        self._pushSaveSets()
        self.visit(node.test)
        self.visit(node.body)
        savedAfterWhileMayBeUninit = self._possiblyUninitialized

        self._peekRestoreSets()
        self.visit(node.orelse)
        savedAfterElseMayBeUninit = self._possiblyUninitialized

        self._popRestoreSets()
        self._possiblyUninitialized.update(savedAfterWhileMayBeUninit)
        self._possiblyUninitialized.update(savedAfterElseMayBeUninit)

    def visit_TryFinally(self, node):
        savedBeforeTryDefinitelyInit = self._definitelyInitialized.copy()
        self.visit(node.body)
        savedAfterTryDefinitelyInit = self._definitelyInitialized
        self._definitelyInitialized = savedBeforeTryDefinitelyInit
        self.visit(node.finalbody)
        # The 'unusual' semantics of try/finally make it that here we
        # use the set-union to update the set of definitely initialized
        # variables, because if control falls through the 'finally' it
        # means it also went through the try/except code without encountering
        # any unhandled exceptions.
        self._definitelyInitialized.update(savedAfterTryDefinitelyInit)

    def visit_TryExcept(self, node):
        sumPossiblyUninit = set()
        sumDefinitelyInit = self._localVars.copy()
        for h in node.handlers:
            self._pushSaveSets()
            self.visit(h)
            sumPossiblyUninit.update(self._possiblyUninitialized)
            sumDefinitelyInit.intersection_update(self._definitelyInitialized)
            self._popRestoreSets()
        self.visit(node.body)
        self.visit(node.orelse)
        self._possiblyUninitialized.update(sumPossiblyUninit)
        self._definitelyInitialized.intersection_update(sumDefinitelyInit)


class _PossiblyUninitializedScopedVisitor(NodeVisitorBases.NodeVisitorBase):
    """Visitor used for collecting possibly uninitialized local variables."""
    def __init__(self):
        self._possiblyUninitializedLocalVariables = set()

    def getPossiblyUninitializedLocalVariables(self):
        return self._possiblyUninitializedLocalVariables

    def _genericVisitScope(self, node):
        self._possiblyUninitializedLocalVariables.update(
            collectPossiblyUninitializedLocalVariablesInScope(node))
        self.generic_visit(node)

    def visit_Module(self, node):
        self._genericVisitScope(node)

    def visit_FunctionDef(self, node):
        self._genericVisitScope(node)

    def visit_Lambda(self, node):
        self._genericVisitScope(node)

    def visit_ClassDef(self, node):
        self._genericVisitScope(node)

    # TODO: We don't need to visit 'expr' sub-trees in search of nested
    # scopes, but there doesn't seem to be a concise way to achieve that.
    # def visit_expr(self, node):
    #    return

def collectPossiblyUninitializedLocalVariables(pyAstNode):
    """Returns the possibly free local variables of the code rooted at `pyAstNode."""
    if not NodeVisitorBases.isScopeNode(pyAstNode):
        raise Exceptions.InternalError(
            "Unsupported type of root node in uninitialized local variable analysis: %s"
            % type(pyAstNode))
    possiblyUninitVisitor = _PossiblyUninitializedScopedVisitor()
    possiblyUninitVisitor.visit(pyAstNode)

    return possiblyUninitVisitor.getPossiblyUninitializedLocalVariables()

