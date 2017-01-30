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

import unittest
import ufora.native.FORA as ForaNative
import ufora.FORA.python.PurePython.PythonAstConverter as PythonAstConverter

addOnePyCode = '''
def addOne(x):
:abd
    return x + 1

addOne(3)
'''

def sourceCodeTree(args):
    if len(args) == 2:
        if args[0].endswith(".script"):
            return ForaNative.SourceCodeTree.Script(args[0][:-7], args[1])
        return ForaNative.SourceCodeTree.Module(args[0], args[1])
    return ForaNative.SourceCodeTree.Module(args[0], args[1], [sourceCodeTree(x) for x in args[2]])

class ModuleParserTest(unittest.TestCase):
    def parse(self, tree, allowPrivate=True):
        parser = ForaNative.ModuleParser()

        if not isinstance(tree, ForaNative.SourceCodeTree):
            tree = sourceCodeTree(tree)

        result = parser.parse(
            tree,
            allowPrivate,
            ForaNative.CodeDefinitionPoint.ExternalFromStringList(["dummy"])
            )

        return result

    def test_root_module_masks_own_variable_names(self):
        sourceCode = sourceCodeTree(("builtin", "f: builtin", []))

        self.assertTrue(len(self.parse(sourceCode).freeVariables) == 0)


    def test_parse_basic(self):
        sourceCode = sourceCodeTree(
            ("builtin", "f:10;", [
                ("math", "a:10;"),
                ("regression", "b:10;")
                ])
            )

        self.assertTrue(len(self.parse(sourceCode).errors) == 0)

    def test_parse_empty_script(self):
        result = self.parse(('module', '', [('a.script', '')]))
        self.assertTrue(result['a'].isMember())

    def test_script_with_no_values_has_no_symbols(self):
        result = self.parse(('module', '', [('a.script', 'let f = 10')]))

        self.assertTrue(result['a'].isMember())
        self.assertTrue(
            len(result['a.module'].asModule.parseMetadata.asScriptModule.symbols) == 0
            )

    def test_parse_single_error(self):
        result = self.parse(('module', 'f: 10; ('))
        self.assertTrue(len(result.errors) == 1)

    def test_parse_multiple_errors(self):
        result = self.parse(('module', 'f: 10; (', [('submodule', '(')]))
        self.assertTrue(len(result.errors) == 2)

    def test_allow_private_symbols(self):
        result1 = self.parse(('module', 'f: ``PrivateSymbol', [('submodule', 'g: ``PrivateSymbol')]), allowPrivate=False)
        result2 = self.parse(('module', 'f: ``PrivateSymbol', [('submodule', 'g: ``PrivateSymbol')]), allowPrivate=True)

        self.assertTrue(len(result1.errors))
        self.assertTrue(len(result2.errors) == 0)

    def test_whole_object_members(self):
        valid = ('root', '', [('module', 'fun() { "this is a valid whole object module member" }')])
        invalid = ('root', '', [
            ('module', 'fun() { "this is a valid whole object module member" }', [
                ('submodule', 'x:10')
                ])
            ])

        self.assertTrue(len(self.parse(valid).errors) == 0)
        self.assertTrue(len(self.parse(invalid).errors) == 1)

    def test_module_with_metadata(self):
        res = self.parse(('module', '"metadata"; x:10'))

        self.assertTrue(res.isModule())
        self.assertTrue(res.asModule.moduleMetadata.getIVC().pyval[1] == "metadata")

    def test_empty_root_module(self):
        res = self.parse(('module', ''))

        self.assertTrue(res.isModule())
        self.assertTrue(len(res.errors) == 0)

    def test_root_module_cannot_be_simple(self):
        res = self.parse(('module', 'fun() { }'))

        self.assertTrue(res.isModule())
        self.assertTrue(len(res.errors) == 1)

    def test_module_with_only_metadata_at_root(self):
        res = self.parse(('module', '"metadata"'))

        self.assertTrue(res.isModule())
        self.assertTrue(res.asModule.moduleMetadata.getIVC().pyval[1] == "metadata")

    def test_script_basic(self):
        res = self.parse(('module', '', [
            ('test.script', "let x = 10; x = x + 1; x")
            ]))

        self.assertTrue(res.isModule())
        script = res.getMembers()['test']

        self.assertTrue(script.asMember.parseMetadata.isWasScript())
        self.assertTrue(str(script.asMember.parseMetadata.asWasScript.scriptModule) == 'test.module')

        scriptModule = res['test.module']

        self.assertTrue(scriptModule.asModule.parseMetadata.isScriptModule())
        symbols = scriptModule.asModule.parseMetadata.asScriptModule.symbols

        self.assertTrue(len(symbols) == 1)

        memberForResult = scriptModule[symbols[0]]
        self.assertTrue(memberForResult.isMember())
        self.assertEqual(memberForResult.asMember.name, symbols[0])

