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

import pyfora.PyAstUninstantiatedVariablesAnalysis as PyAstUninstantiatedVariablesAnalysis
import pyfora.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import pyfora.Exceptions as Exceptions
import ast
import textwrap
import unittest

class PyAstPossiblyUninitializedVariables_test(unittest.TestCase):
    def test_member_acces_after_possible_assignment(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f():
                    if 0:
                       x = 2
                    x.y
                """
                )
            )
        expectedResult = set(['x'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

        self.assertEqual(
            set(),
            PyAstFreeVariableAnalyses.getFreeVariables(tree)
            )

        self.assertEqual(
            set(),
            PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(tree)
            )        

    def test_possiblyUninitializedVariables_assignToSelf(self):
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
        expectedResult = set(['x', 'y', 'z'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_Assign(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    tr, (v0, v1) = x
                    v2 = v3 = y
                    v4 = x + y
                    return tr + v0 + v1 + v2 + v3 + v4
                """
                )
            )
        expectedResult = set([])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_Augassign(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    tr1 = 0
                    tr1 += x + y
                    tr2 += x + y
                    return tr1 + tr2
                """
                )
            )
        expectedResult = set(['tr2'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_If(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x):
                    if x:
                        y = 2
                    return y
                """
                )
            )
        expectedResult = set(['y'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_NestedIf_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    if x:
                        if y:
                            z = x * y
                        else:
                            z = x + y
                    else:
                        if y:
                            z = x + y
                        else:
                            z = 2
                    return z
                """
                )
            )
        expectedResult = set([])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_NestedIf_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    if x:
                        if y:
                            z = x * y
                        else:
                            z = x + y
                    else:
                        if y:
                            z = x + y
                    return z
                """
                )
            )
        expectedResult = set(['z'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_For(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    for z in range(v0, v1):
                        tr = z
                    return tr
                """
                )
            )
        expectedResult = set(['tr'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_While(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    while z in range(v0, v1):
                        tr = z
                    return tr
                """
                )
            )
        expectedResult = set(['tr'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_TryExceptFinally_1(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    u0 = 0
                    try:
                        v1 = 0
                        u1 = u2 = u3 = u4 = 0
                    except Exception:
                        v1 = u2
                        v2 = u0
                    except Exception:
                        v1 = u3
                        v2 = u0
                    else:
                        v2 = u1
                    finally:
                        v3 = u4
                    return v1 + v2 + v3
                """
                )
            )
        expectedResult = set(['u2', 'u3', 'u4'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_TryExceptFinally_2(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    try:
                        v1 = 0
                    except Exception as e1:
                        v1 = 1
                        v2 = e1
                    except Exception as e2:
                        v4 = e1
                        v2 = e2
                    else:
                        v2 = 0
                    finally:
                        v3 = x
                    return v1 + v2 + v3
                """
                )
            )
        expectedResult = set(['v1', 'e1'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_TryExceptFinally_3(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    try:
                        v1 = 0
                    except Exception as e1:
                        v1 = 1
                        v2 = e1
                    except Exception as e2:
                        v4 = e1
                        v2 = e2
                    finally:
                        e1 = 0
                        v3 = x
                    return v1 + v2 + v3
                """
                )
            )
        expectedResult = set(['v1', 'v2', 'e1'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_TryExceptFinally_4(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    v1 = u1
                    try:
                        v2 = u2
                    finally:
                        e1 = u3
                        v3 = v2
                    v4 = u4
                    u1 = u2 = u3 = u4 = 0
                    return v1 + v2 + v3
                """
                )
            )
        expectedResult = set(['u1', 'u2', 'u3', 'u4', 'v2'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_TryExceptFinally_5(self):
        tree = ast.parse(
            textwrap.dedent(
                """def f(x, y):
                    v1 = u1
                    try:
                        v2 = u2
                    finally:
                        e1 = u3
                        v3 = u4
                    v4 = u4
                    u1 = u2 = u3 = u4 = 0
                    return v1 + v2 + v3
                """
                )
            )
        expectedResult = set(['u1', 'u2', 'u3', 'u4'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
            )
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.
                collectPossiblyUninitializedLocalVariables(tree)
            )

    def test_possiblyUninitializedVariables_Exceptions(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                x = 1
                def f(x, y):
                    return v1 + v2 + v3
                """
                )
            )
        with self.assertRaises(Exceptions.InternalError):
            PyAstUninstantiatedVariablesAnalysis.\
                collectPossiblyUninitializedLocalVariablesInScope(tree.body[0])
        with self.assertRaises(Exceptions.InternalError):
            PyAstUninstantiatedVariablesAnalysis.\
                collectPossiblyUninitializedLocalVariables(tree.body[0])

    def test_possiblyUninitializedVariables_CompsAndGenExp1(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                [elt1 for elt1 in container1]
                {elt2 for elt2 in container2}
                {elt3: elt4 for elt4 in container4 for elt3 in container3}
                (x*y for x in range(10) for y in bar(x))
                """
                )
            )
        expectedResult = set([])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.collectPossiblyUninitializedLocalVariables(tree)
        )

    def test_possiblyUninitializedVariables_CompsAndGenExp2(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                [elt01 for elt1 in container1]
                {elt02 for elt2 in container2}
                {elt03: elt04 for elt4 in container4 for elt3 in container3}
                (x0*y0 for x in range(10) for y in bar(x))
                """
                )
            )
        expectedResult = set([])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.collectPossiblyUninitializedLocalVariables(tree)
        )

    def test_possiblyUninitializedVariables_forLoop(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                def f1():
                    y1 = 0
                    for x1 in [1,2,3,4]:
                        y1 = y1 + x1
                    else:
                        x1 = -1
                    return (y1,x1)
                def f2():
                    y2 = 0
                    x2 = 0
                    for x2 in [1,2,3,4]:
                        y2 = y2 + x2
                    else:
                        x2 = -1
                    return (y2,x2)
                def f3():
                    y3 = 0
                    while f1() :
                        x3 = 1
                        y3 = y3 + x3
                    else:
                        x3 = -1
                    return (y3,x3)
                """
                )
            )
        expectedResult = set(['x1', 'x3'])
        self.assertEqual(
            expectedResult,
            PyAstUninstantiatedVariablesAnalysis.collectPossiblyUninitializedLocalVariables(tree)
        )


if __name__ == "__main__":
    unittest.main()

