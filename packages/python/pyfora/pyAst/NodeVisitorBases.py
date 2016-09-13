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

import ast
import collections
import pyfora.Exceptions as Exceptions

class VisitDone(Exception):
    """Raise this exception to short-circuit the visitor once we're done searching."""
    pass

def isScopeNode(pyAstNode):
    """Return true iff argument is a scoped node."""
    if isinstance(pyAstNode, (ast.Module, ast.ClassDef,
                              ast.FunctionDef, ast.Lambda, ast.GeneratorExp)):
        return True
    else:
        return False

PositionInFile = collections.namedtuple('PositionInFile', ['lineno', 'col_offset'])

##########################################################################
# Context Managers
class InScopeSaveRestoreValue(object):
    """Generic Context Manager for simple GenericInScopeVisitors."""
    def __init__(self, valueGetter, valueSetter):
        self._valueGetter = valueGetter
        self._valueSetter = valueSetter
        self._stash = []
        self.newValue = None

    def __enter__(self):
        oldValue = self._valueGetter()
        self._stash.append(oldValue)
        self._valueSetter(self.newValue)
    def __exit__(self, exc_type, exc_value, traceback):  # exit scope
        savedValue = self._stash.pop()
        self._valueSetter(savedValue)


class ScopedSaveRestoreComputedValue(object):
    """ Generic Context Manager for GenericScopedVisitors."""
    def __init__(self, valueGetter, valueSetter, valueComputer):
        """
        valueGetter: function that returns the current value
        valueSetter: function that takes a value and sets it as current
        valueComputer: function that takes (node, old_value) and computes new value
        """
        self.valueGetter = valueGetter
        self.valueSetter = valueSetter
        self.valueComputer = valueComputer
        self.root = None
        self._stash = []
    def __enter__(self):
        oldValue = self.valueGetter()
        self._stash.append(oldValue)
        newValue = self.valueComputer(self.root, oldValue)
        self.valueSetter(newValue)
    def __exit__(self, exc_type, exc_value, traceback):  # exit scope
        savedValue = self._stash.pop()
        self.valueSetter(savedValue)

##########################################################################
# Visitor Base Classes
class SemanticOrderNodeVisitor(ast.NodeVisitor):
    """Modifies ast.NodeVisitor visitation order and enables to visit lists of ast.Node."""
    def generic_visit(self, node):
        if isinstance(node, list):
            self._generic_visit_list(node)
        else:
            super(SemanticOrderNodeVisitor, self).generic_visit(node)

    def _generic_visit_list(self, node):
        for item in node:
            if isinstance(item, ast.AST):
                self.visit(item)

    # For assignments, visit RHS first
    def visit_Assign(self, node):
        self.visit(node.value)
        self.visit(node.targets)

    def visit_AugAssign(self, node):
        self.visit(node.value)
        self.visit(node.target)

    def visit_ListComp(self, node):
        self.visit(node.generators)
        self.visit(node.elt)

    def visit_SetComp(self, node):
        self.visit(node.generators)
        self.visit(node.elt)

    def visit_GeneratorExp(self, node):
        self.visit(node.generators)
        self.visit(node.elt)

    def visit_DictComp(self, node):
        self.visit(node.generators)
        self.visit(node.key)
        self.visit(node.value)

class SemanticOrderNodeTransvisitor(ast.NodeTransformer):
    """Modifies ast.NodeTransformer visitation order and enables to visit lists of ast.Node.

    It is called a 'transvisitor' because it implements a transformer but only
    performs a visit (i.e., it does not modify the ast)
    """
    def generic_visit(self, node):
        if isinstance(node, list):
            return self._generic_visit_list(node)
        else:
            return super(SemanticOrderNodeTransvisitor, self).generic_visit(node)

    def _generic_visit_list(self, node):
        res = []
        modified = False
        for item in node:
            if isinstance(item, ast.AST):
                new_item = self.visit(item)
                res.append(new_item)
                if new_item is not item:
                    modified = True
        if not modified:
            return node
        else:
            return res

    # For assignments, visit RHS first
    def visit_Assign(self, node):
        value = self.visit(node.value)
        targets = self.visit(node.targets)
        if value is node.value and targets is node.targets:
            return node
        else:
            return ast.copy_location(
                        ast.Assign(targets=targets,
                                   value=value),
                        node)

    def visit_AugAssign(self, node):
        value = self.visit(node.value)
        operator = self.visit(node.op)
        target = self.visit(node.target)
        if value is node.value and operator is node.op and target is node.target:
            return node
        else:
            return ast.copy_location(
                        ast.AugAssign(target=target,
                                      operator=operator,
                                      value=value),
                        node)

    def visit_ListComp(self, node):
        generators = self.visit(node.generators)
        elt = self.visit(node.elt)
        if generators is node.generators and elt is node.elt:
            return node
        else:
            return ast.copy_location(
                        ast.ListComp(elt=elt,
                                     generators=generators),
                        node)

    def visit_SetComp(self, node):
        generators = self.visit(node.generators)
        elt = self.visit(node.elt)
        if generators is node.generators and elt is node.elt:
            return node
        else:
            return ast.copy_location(
                        ast.SetComp(elt=elt,
                                    generators=generators),
                        node)

    def visit_GeneratorExp(self, node):
        generators = self.visit(node.generators)
        elt = self.visit(node.elt)
        if generators is node.generators and elt is node.elt:
            return node
        else:
            return ast.copy_location(
                        ast.GeneratorExp(elt=elt,
                                         generators=generators),
                        node)


    def visit_DictComp(self, node):
        generators = self.visit(node.generators)
        key = self.visit(node.key)
        value = self.visit(node.value)
        if key is node.key and value is node.value and generators is node.generators:
            return node
        else:
            return ast.copy_location(
                        ast.DictComp(key=key,
                                     value=value,
                                     generators=generators),
                        node)

class GenericInScopeVisitor(SemanticOrderNodeVisitor):
    """Shallow visitor that does not descend into sub-scopes.

    It is initialized with the root of the AST to visit, which must be
    a scoped node (Module, Class, FunctionDef, or Lambda), and it implements
    `_cachedCompute` which ensures the visit is performed once.
    This visitor also keeps track of whether we are visiting the left-hand-side
    of an assignment, which can be used by visitors extending it.
    """
    def __init__(self, node):
        self._root = node
        self._isInDefinition = False

        self._isInDefinitionValueManager = \
            InScopeSaveRestoreValue(
                self.getIsInDefinition,
                self._setIsInDefinition)
        self._isComputed = False

    def getIsInDefinition(self):
        return self._isInDefinition
    def _setIsInDefinition(self, value):
        self._isInDefinition = value
    def _isInDefinitionMgr(self, newValue=True):
        self._isInDefinitionValueManager.newValue = newValue
        return self._isInDefinitionValueManager

    def _cachedCompute(self):
        if not self._isComputed:
            if isScopeNode(self._root):
                if isinstance(self._root, ast.FunctionDef) and hasattr(self._root, 'arguments'):
                    self._root.arguments.lineno = self._root.lineno
                    self._root.arguments.col_offset = self._root.col_offset
                self.generic_visit(self._root)
                self._isComputed = True
            else:
                raise Exceptions.InternalError(
                        "'%s' called on unsupported node-type (%s)"
                        % (self.__class__.__name__, type(self._root))
                    )

    # # BINDING:
    # The following constructs bind names:
    #   formal parameters to functions,
    #   import statements,
    #   class and function definitions (these bind their name in the defining block),
    #   and targets that are identifiers if occurring in:
    #                an assignment,
    #                for loop header,
    #                in the second position of an except clause header
    #                or after as in a with statement.
    #                Comprehensions (Set,List,Dict)
    # TODO: The import statement of the form from ... import * binds all names
    #     defined in the imported module, except those beginning with an underscore.
    #     This form may only be used at the module level.

    def visit_Module(self, _):
        return

    def visit_FunctionDef(self, _):
        return

    def visit_ClassDef(self, _):
        return

    def visit_Lambda(self, _):
        return

    def visit_GeneratorExp(self, _):
        return

    def visit_Assign(self, node):
        self.visit(node.value)
        with self._isInDefinitionMgr():
            self.visit(node.targets)

    def visit_AugAssign(self, node):
        self.visit(node.value)
        with self._isInDefinitionMgr():
            self.visit(node.target)

    def visit_For(self, node):
        with self._isInDefinitionMgr():
            self.visit(node.target)
        self.visit(node.iter)
        self.visit(node.body)
        self.visit(node.orelse)

    # With(expr context_expr, expr? optional_vars, stmt* body)
    def visit_With(self, node):
        self.visit(node.context_expr)
        with self._isInDefinitionMgr():
            if node.optional_vars is not None:
                self.visit(node.optional_vars)
        self.visit(node.body)

    def visit_Attribute(self, node):
        with self._isInDefinitionMgr(False):
            self.visit(node.value)

    def visit_Global(self, _):
        raise Exceptions.PythonToForaConversionError(
            "Illegal 'global' statement: not supported in Python to Fora translation.")

    # ExceptHandler(expr? type, expr? name, stmt* body)
    def visit_ExceptHandler(self, node):
        if node.type is not None:
            self.visit(node.type)  # we probably don't need to visit it
        if node.name is not None:
            with self._isInDefinitionMgr():
                self.visit(node.name)
        self.visit(node.body)

    # arguments = (expr* args, identifier? vararg, identifier? kwarg, expr* defaults)
    def visit_arguments(self, node):
        self.visit(node.defaults)
        with self._isInDefinitionMgr():
            self.visit(node.args)

    # comprehension = (expr target, expr iter, expr* ifs)
    def visit_comprehension(self, node):
        with self._isInDefinitionMgr():
            self.visit(node.target)
        self.visit(node.iter)
        self.visit(node.ifs)


class GenericScopedTransvisitor(SemanticOrderNodeTransvisitor):
    """
    Base class for two-pass transformers.

    Before entering a new scope, update a value (e.g., bound values) by running a 
    visitor on the new scope and possibly taking account of the old value. Upon
    returning back to the outer scope, restore the value. All of this happens 
    through a context manager, for example the class ScopedSaveRestoreComputedValue
    provided above.
    """
    def __init__(self, scopeMgr):
        self._scopeMgr = scopeMgr

    def _getScopeMgr(self, node):
        self._scopeMgr.root = node
        return self._scopeMgr
    # VISITORS
    def visit_Module(self, node):
        with self._getScopeMgr(node):
            body = self.visit(node.body)
            if body is node.body:
                return node
            else:
                print 'making a fresh Module node'
                return ast.copy_location(
                            ast.Module(body=body),
                            node)

    def visit_FunctionDef(self, node):
        node.args.lineno = node.lineno
        node.args.col_offset = node.col_offset
        defaults = self.visit(node.args.defaults)
        if defaults is node.args.defaults:
            args = node.args
        else:
            args = ast.arguments(args=node.args.args,
                                 defaults=defaults,
                                 vararg=node.args.vararg,
                                 kwarg=node.args.kwarg)
        with self._getScopeMgr(node):
            body = self.visit(node.body)
            decorator_list = self.visit(node.decorator_list)
            if body is node.body and decorator_list is node.decorator_list and args is node.args:
                return node
            else:
                return ast.copy_location(
                            ast.FunctionDef(name=node.name,
                                            args=args,
                                            body=body,
                                            decorator_list=decorator_list),
                            node)

    def visit_Lambda(self, node):
        node.args.lineno = node.lineno
        node.args.col_offset = node.col_offset
        defaults = self.visit(node.args.defaults)
        if defaults is node.args.defaults:
            args = node.args
        else:
            args = ast.arguments(args=node.args.args,
                                 defaults=defaults,
                                 vararg=node.args.vararg,
                                 kwarg=node.args.kwarg)
        with self._getScopeMgr(node):
            body = self.visit(node.body)
            if body is node.body and args is node.args:
                return node
            else:
                return ast.copy_location(
                            ast.Lambda(args=args,
                                       body=body),
                            node)

    def visit_GeneratorExp(self, node):
        with self._getScopeMgr(node):
            generators = self.visit(node.generators)
            elt = self.visit(node.elt)
            if generators is node.generators and elt is node.elt:
                return node
            else:
                return ast.copy_location(
                            ast.GeneratorExp(elt=elt,
                                             generators=generators),
                            node)

    def visit_ClassDef(self, node):
        bases = self.visit(node.bases)
        body = self.visit(node.body)
        decorator_list = self.visit(node.decorator_list)
        if bases is node.bases and body is node.body and decorator_list is node.decorator_list:
            return node
        else:
            return ast.copy_location(
                        ast.ClassDef(name=node.name,
                                     bases=bases,
                                     body=body,
                                     decorator_list=decorator_list),
                        node)
