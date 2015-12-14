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

import pyfora.pyAst.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import ast
import textwrap
import unittest

class PyAstCollectBoundVariablesInScope_test(unittest.TestCase):
    def test_CollectBoundVariablesInScope_block(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                    v1
                    v2 = 2
                    v3 += 3
                    (v4, v5), v6 = w
                    for v7 in range(0,10):
                        v8 = z
                    v9 = [v10 for v11 in v12]
                    v13 = { v14 for v15 in v16 }
                    v17 = { v18:v19 for v20 in v21 for v22 in v23 }
                """
                )
            )

        self.assertEqual(
            set(['v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v11',
                 'v13', 'v15', 'v17', 'v20', 'v22']),
            PyAstFreeVariableAnalyses.collectBoundVariablesInScope(tree)
            )

    def test_CollectBoundVariablesInScope_functionDef(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                v0 = z
                def f(x):
                    v1
                    v2 = 2
                    v3 += 3
                    (v4, v5), v6 = w
                v7 = zz
                """
                )
            )

        self.assertEqual(
            set(['v0', 'v7']),
            PyAstFreeVariableAnalyses.collectBoundVariablesInScope(tree)
            )
        self.assertEqual(
            set(['f']),
            PyAstFreeVariableAnalyses.collectBoundNamesInScope(tree)
            )

    def test_CollectBoundVariablesInScope_classDef(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                v0 = z
                class c(x):
                    v1
                    v2 = 2
                    v3 += 3
                    (v4, v5), v6 = w
                v7 = zz
                """
                )
            )

        self.assertEqual(
            set(['v0', 'v7']),
            PyAstFreeVariableAnalyses.collectBoundVariablesInScope(tree)
            )
        self.assertEqual(
            set(['c']),
            PyAstFreeVariableAnalyses.collectBoundNamesInScope(tree)
            )


    def test_CollectBoundVariablesInScope_tryExceptWith(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                try:
                    with y as z:
                        x += 1
                except Exception as e:
                    print e.message
                except ValueError:
                    print "Wrong Value"
                """
                )
            )

        self.assertEqual(
            set(['x', 'e', 'z']),
            PyAstFreeVariableAnalyses.collectBoundVariablesInScope(tree)
            )


if __name__ == "__main__":
    unittest.main()

