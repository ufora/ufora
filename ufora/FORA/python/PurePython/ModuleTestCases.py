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


class ModuleTestCases(object):
    """Test cases for pyfora modules"""

    def test_imports_1(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithImport \
            as ModuleWithImport

        self.equivalentEvaluationTest(ModuleWithImport.h, 2)

    def test_imports_2(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithOneMember \
            as ModuleWithOneMember

        def f(x):
            return ModuleWithOneMember.h(x)

        self.equivalentEvaluationTest(f, 2)

    def test_closures_1(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithClosures1 \
            as ModuleWithClosures1

        self.equivalentEvaluationTest(ModuleWithClosures1.f1, 3, 4)

    def test_closures_2(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithClosures2 \
            as ModuleWithClosures2

        self.equivalentEvaluationTest(ModuleWithClosures2.f2(3), 4)

    def test_mutuallyRecursiveModuleMembers_1(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers1 \
            as MutuallyRecursiveModuleMembers1

        self.equivalentEvaluationTest(MutuallyRecursiveModuleMembers1.f, 2)

    def test_mutuallyRecursiveModuleMembers_2(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers2 \
            as MutuallyRecursiveModuleMembers2

        self.equivalentEvaluationTest(MutuallyRecursiveModuleMembers2.f4, 109)

    def test_mutuallyRecursiveModuleMembers_3(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers3 \
            as MutuallyRecursiveModuleMembers1

        self.equivalentEvaluationTest(MutuallyRecursiveModuleMembers1.f, 5)

    def test_import_example(self):
        import ufora.FORA.python.PurePython.testModules.import_example.B as B

        self.equivalentEvaluationTest(lambda: B.f(2))


