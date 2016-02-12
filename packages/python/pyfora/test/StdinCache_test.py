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

import pyfora.StdinCache as StdinCache
import ast
import textwrap
import unittest

def dedentAndStrip(text):
    lines = textwrap.dedent(text).split("\n")
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)

class StdinCache_test(unittest.TestCase):
    def test_stdinCache(self):
        stdinCache = StdinCache.StdinCache()
        stdinCache.refreshFromText(
            dedentAndStrip(
                """
                x
                y
                """
                )
            )
        self.assertEqual(len(stdinCache.blocks), 2)

    def test_stdinCache_trailing_backslash(self):
        stdinCache = StdinCache.StdinCache()
        stdinCache.refreshFromText(
            dedentAndStrip(
                """
                x+\
                y
                """
                )
            )
        self.assertEqual(len(stdinCache.blocks), 1)

    def test_stdinCache_trailing_backslash_2(self):
        stdinCache = StdinCache.StdinCache()
        stdinCache.refreshFromText(
            dedentAndStrip(
                """
                x+\
                z+\
                y
                """
                )
            )
        self.assertEqual(len(stdinCache.blocks), 1)

    def test_stdinCache_trailing_backslash_3(self):
        stdinCache = StdinCache.StdinCache()
        stdinCache.refreshFromText(
            dedentAndStrip(
                """
                x+\
                z+\
                y
                f+\
                g+\
                h
                """
                )
            )
        self.assertEqual(len(stdinCache.blocks), 2)

    def test_stdinCache_2(self):
        stdinCache = StdinCache.StdinCache()
        stdinCache.refreshFromText(
            dedentAndStrip(
                """
                def f(arg):
                    if arg:
                        x.y = 3
                    return x

                f()

                """
                )
            )
        self.assertEqual(len(stdinCache.blocks), 3, stdinCache.blocks)
        self.assertEqual(len(stdinCache.blocks[0]), 4)

    def test_stdinCache_find(self):
        stdinCache = StdinCache.StdinCache()
        stdinCache.refreshFromText(
            dedentAndStrip(
                """
                x+y

                z+h

                def f():
                    def g():
                        return 10
                    return g
                """
                )
            )

        e1 = compile(ast.parse("x+y"), "<stdin>", 'exec')
        e2 = compile(ast.parse("z+h"), "<stdin>", 'exec')

        self.assertEqual(stdinCache.findCodeLineNumberWithinStdin(e1),0)
        self.assertEqual(stdinCache.findCodeLineNumberWithinStdin(e2),2)

        def f():
            def g():
                return 10
            return g

        g = f()

        self.assertEqual(stdinCache.findCodeLineNumberWithinStdin(f.func_code), 4)
        self.assertEqual(stdinCache.findCodeLineNumberWithinStdin(g.func_code), 5)


if __name__ == "__main__":
    unittest.main()
