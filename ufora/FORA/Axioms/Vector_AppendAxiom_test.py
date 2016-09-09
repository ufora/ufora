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

import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.Runtime as Runtime
import ufora.native.FORA as FORANative
import ufora.native.CallbackScheduler as CallbackScheduler

class TestAppendAxiom(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime.getMainRuntime()
        self.axioms = self.runtime.getAxioms()
        self.native_runtime = self.runtime.getTypedForaCompiler()
        self.vdm = FORANative.VectorDataManager(CallbackScheduler.singletonForTesting(), 10000000)

    def test_repeated_calls_to_vector_of_vector_creation_1(self):
        FORA.eval("let i = 0; while (i < 10000) { [[1]]; i = i + 1; }")

    def test_repeated_calls_to_vector_of_vector_creation_2(self):
        FORA.eval("let v = []; let v2 = [1]; let i = 0; while (i < 10000) { [v2]; i = i + 1; }; v")

    def test_repeated_calls_to_vector_of_vector_creation_3(self):
        FORA.eval("let i = 0; while (i < 10000) { fun(){[[1]]}(); i = i + 1; }")

    def test_yet_another_vector_bug(self):
        FORA.eval("let v = [3,3,3]; v :: [1]")

    def test_yet_another_vector_bug2(self):
        FORA.eval("let v = [3,3,3]; v `(`append,[1])")

