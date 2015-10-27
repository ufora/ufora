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

import ufora.FORA.python.PurePython.PythonAstConverter as PythonAstConverter

import unittest
import ufora as ufora

def allSubmodules(module, modulesSoFar = None):
    if modulesSoFar is None:
        modulesSoFar = set()

    for name in dir(module):
        child = getattr(module, name)
        if type(child) is type(ufora):
            if child not in modulesSoFar:
                modulesSoFar.add(child)
                allSubmodules(child, modulesSoFar)

    return list(modulesSoFar)



class PythonAstConverterTest(unittest.TestCase):
    def test_python_ast_conversion_lots_of_code(self):
        modules = allSubmodules(ufora)
        filenames = []
        for m in modules:
            if '__file__' in dir(m):
                filename = m.__file__
                if filename.endswith(".pyc"):
                    filename = filename[:-4] + ".py"

                if filename.endswith(".py"):
                    filenames.append(filename)
        filenames = sorted(filenames)

        for filename in filenames:
            print filename
            with open(filename, "r") as f:
                txt = f.read()
                if txt:
                    PythonAstConverter.parseStringToPythonAst(txt)

