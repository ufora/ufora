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



class EquivalentEvaluationTestCases:
    """EquivalentEvaluationTestCases - mixin to define equivalent evaluation test cases"""
    
    def equivalentEvaluationTest(self, func, *args):
        raise NotImplementedError()

    def test_define_function(self):
        def f(x):
            return x+1
        arg = 4

        self.equivalentEvaluationTest(f, arg)

    def test_repeatedEvaluation(self):
        def f(x):
            return x+1
        arg = 4

        for _ in range(10):
            self.equivalentEvaluationTest(f, arg)

    def test_tuple_conversion(self):
        def f(x):
            return (x, x+1)

        self.equivalentEvaluationTest(f, 10)

    def test_submit_function_call(self):
        def f(x):
            return x+1
        arg = 4
        self.equivalentEvaluationTest(f, arg)

    def test_class_member_functions(self):
        class ClassTest0:
            def __init__(self,x):
                self.x = x

            def f(self):
                return 10

        def testFun():
            c = ClassTest0(10)
            return c.x

        self.equivalentEvaluationTest(testFun)

    def test_class_member_semantics(self):
        def f():
            return 'free f'

        y = 'free y'

        class ClassTest1:
            def __init__(self, y):
                self.y = y

            def f(self):
                return ('member f', y, self.y)

            def g(self):
                return (f(), self.f())

        def testFun():
            c = ClassTest1('class y')
            return c.g()

        self.equivalentEvaluationTest(testFun)

