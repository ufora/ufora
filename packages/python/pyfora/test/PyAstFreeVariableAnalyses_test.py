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

import pyfora.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import pyfora.Exceptions as Exceptions
import pyfora.PyAstUtil as PyAstUtil
import ast
import textwrap
import unittest

class PyAstFreeVariableAnalyses_test(unittest.TestCase):
    def test_freeVariables_assignToSelf(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                x = x
                def f():
                    y = y
                    class C(object):
                        z = z
                """
                )
            )

        self.assertEqual(
            set(['object', 'z']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_classLocalVar_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                class C(object):
                    x = 0
                """
                )
            )

        self.assertEqual(
            set(['object']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_classLocalVar_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                class C(object):
                    x = 0
                    y = x
                """
                )
            )

        self.assertEqual(
            set(['object']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_classLocalVar_3(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                class C(object):
                    x = x
                    y = x
                """
                )
            )

        self.assertEqual(
            set(['x', 'object']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_functionDef_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y = z, w = unbound, *args, **kwargs):
                    z = 2
                    z + args + x + y + kwargs
                    x = args + kwargs
                    nonExistent1 += 2
                    nonExistent2 = 2
                    nonExistent3
                """
                )
            )

        self.assertEqual(
            set(['z', 'unbound', 'nonExistent3']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_functionDef_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """def outer():
                    def f(x):
                        return len(f)"""
                )
            )

        self.assertEqual(
            set(['len']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_classDef_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """class C(object):
                    def f(x):
                        return len(f)"""
                )
            )

        self.assertEqual(
            set(['object', 'len', 'f']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_classDef_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                @decorator
                class C(B, D):
                    def f(self):
                        return self.g + C + g
                    def g(self):
                        return 0"""
                )
            )

        self.assertEqual(
            set(['g', 'decorator', 'B', 'D']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_classDef_3(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                @decorator
                class C(B, D):
                    def g(self):
                        return 0
                    def f(self):
                        return self.g + C + g
                """
                )
            )

        self.assertEqual(
            set(['g', 'decorator', 'B', 'D']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_classDef_decorator(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                class C10:
                    @staticmethod
                    def g(x):
                        return x + 1
                    def f(self, arg):
                        return C10.g(arg)
                """
                )
            )

        self.assertEqual(
            set(['staticmethod']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_For(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                for x in elt:
                    x + 2
                """
                )
            )

        self.assertEqual(
            set(['elt']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Assign(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                (x, y), z = w
                """
                )
            )

        self.assertEqual(
            set(['w']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )
        
    def test_freeVariables_Sequence_1(self):
        # this might seem a little strange,
        # but ast parses this as a module

        tree = ast.parse(
            textwrap.dedent(
                """
                x = 2
                x + 3
                """
                )
            )

        self.assertEqual(
            set(),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Sequence_2(self):
        # this might seem a little strange,
        # but ast parses this as a module

        tree = ast.parse(
            textwrap.dedent(
                """
                def f(arg):
                    return arg + x
                x = 3
                """
                )
            )

        self.assertEqual(
            set(),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Sequence_3(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f():
                    x + 2
                    x = 3
                """
                )
            )

        self.assertEqual(
            set([]),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Sequence_4(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f():
                    x = 3
                    x + 2
                """
                )
            )

        self.assertEqual(
            set(),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Sequence_5(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                class C:
                    x = 2
                    def fn(self, arg):
                        return arg + x
                    fn
                """
                )
            )

        self.assertEqual(
            set(['x', 'fn']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Sequence_6(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                class C:
                    def f(self, arg):
                        return arg + x
                    x = 2
                    f
                """
                )
            )

        self.assertEqual(
            set(['x', 'f']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Sequence_7(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def func():
                    def f(self, arg):
                        return arg + x
                    x = 2
                    f
                    class C:
                        pass
                    C
                """
                )
            )

        self.assertEqual(
            set([]),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_Lambda_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                lambda x, y = z, *args, **kwargs: (x, y, args, kwargs, free)
                """
                )
            )

        self.assertEqual(
            set(['z', 'free']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_ListComp_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                [val for val in x if val == free]
                """
                )
            )

        self.assertEqual(
            set(['x', 'free']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )
        
    def test_freeVariables_ListComp_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                [val for val in x if val == free]
                """
                )
            )

        self.assertEqual(
            set(['free', 'x']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )
        
    def test_freeVariables_ListComp_3(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                x = [1,2,3]
                [y for val in x]
                """
                )
            )

        self.assertEqual(
            set(['y']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_ListComp_4(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                [(x, y) for x in [1,2,3] for y in [3,1,4] if x != y]
                """
                )
            )
        
        self.assertEqual(
            set(),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_SetComp_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                {v for x in q}
                """
                )
            )

        self.assertEqual(
            set(['v', 'q']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_DictComp_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                d = { x: y for x, y in o.f() }
                """
                )
            )

        self.assertEqual(
            set(['o']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_DictComp_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                d = { x1: y1 for x2, y2 in o.f() }
                """
                )
            )

        self.assertEqual(
            set(['o', 'x1', 'y1']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_functionCalls(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                x = 2
                f(x, y, z = 2, w = x, q = free, *args, **kwargs)
                """
                )
            )

        self.assertEqual(
            set(['f', 'y', 'args', 'kwargs', 'free']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )
    
    def test_freeVariables_nestedScopes_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(x):
                  y = 2
                  class C:
                    def g(self, arg):
                      x + y + arg
                """
                )
            )

        self.assertEqual(
            set([]),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_nestedScopes_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x):
                    y = x + z
                    o.notFree = 3
                    class C:
                        def g(self):
                            return w + f(x) + C
                    C
                """
                )
            )

        self.assertEqual(
            set(['z', 'w', 'o']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_nestedScopes_3(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(x):
                  y = 2
                  class C:
                    def g(self, arg):
                      x + y + arg
                C
                """
                )
            )

        self.assertEqual(
            set(['C']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    # In the following two tests, 'x' within function 'f' is local,
    # regardless to whether there is a global 'x' in a parent scope.
    def test_freeVariables_notFreeNotDefinedOnAllPaths_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                x = 42
                def f(arg):
                    if arg:
                        x = 3
                    return x
                """
                )
            )
        self.assertEqual(
            set([]),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_notFreeNotDefinedOnAllPaths_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(arg):
                    if arg:
                        x = 3
                    return x
                """
                )
            )
        self.assertEqual(
            set([]),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_globalStmt_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f():
                    global x
                    x = 3
                    return x
                """
                )
            )
        with self.assertRaises(Exceptions.PythonToForaConversionError):
            PyAstFreeVariableAnalyses.getFreeVariables(tree)

    def test_freeVariables_globalStmt_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f():
                    global x
                    return x
                """
                )
            )
        with self.assertRaises(Exceptions.PythonToForaConversionError):
            PyAstFreeVariableAnalyses.getFreeVariables(tree)

    def test_freeVariables_forLoop(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(arg):
                    tr = x
                    for x in xrange(0, arg):
                        tr += x
                    return tr
                """
                )
            )
        self.assertEqual(
            set(['xrange']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_whileLoop(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(arg):
                    tr = 0
                    while x in range(0, arg):
                        tr += 1
                    return tr
                """
                )
            )
        self.assertEqual(
            set(['x', 'range']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_inAssignment(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(arg):
                    y = x
                    return y
                """
                )
            )
        self.assertEqual(
            set(['x']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_withStatement(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(arg):
                    with x as e:
                        return e
                """
                )
            )
        self.assertEqual(
            set(['x']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_tryExcept(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f(x):
                    try:
                        x += 1 
                    except Exception as e:
                        print e.message
                    except ValueError:
                        print "Wrong Value"
                    finally:
                        x -= 1
                    return x
                """
                )
            )
        self.assertEqual(
            set(['Exception', 'ValueError']),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

    def test_freeVariables_onFunctionDefNode(self):
        tree1 = ast.parse(
            textwrap.dedent(
                """
                def g(arg):
                    if arg < 0:
                        return x + arg
                    return x * h(arg - 1, g)
                """
                )
            )

        res = PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(tree1)
        self.assertEqual(
            set([('h',), ('x',)]),
            res
            )

        tree2 = PyAstUtil.functionDefAtLineNumber(tree1, 2)

        self.assertEqual(
            set([('h',), ('x',)]),
            PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(tree2, False)
            )

    def test_freeVariableMemberAccessChain_1(self):
        tree = ast.parse("x.y.z.w")

        self.assertEqual(
            ('x', 'y', 'z', 'w'),
            PyAstFreeVariableAnalyses._freeVariableMemberAccessChain(
                tree.body[0].value
                )
            )

    def test_freeVariableMemberAccessChain_2(self):
        tree = ast.parse("(1).y.z.w")

        self.assertIsNone(
            PyAstFreeVariableAnalyses._freeVariableMemberAccessChain(
                tree.body[0].value
                )
            )
    def test_freeVariableMemberAccessChains_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f():
                  x
                  x = 2
                  def f(x):
                    x.y
                    z.w.q
                """
                )
            )

        res = PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(tree)

        self.assertEqual(
            set([('z', 'w', 'q')]),
            res
            )

    def test_freeVariableMemberAccessChains_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f():
                  y = 2
                  class C:
                    def g(self, arg):
                      x.y.z + y + arg
                  x = 2
                C.f
                """
                )
            )

        res = PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(tree)

        self.assertEqual(
            set([('C', 'f')]),
            res
            )

if __name__ == "__main__":
    unittest.main()




