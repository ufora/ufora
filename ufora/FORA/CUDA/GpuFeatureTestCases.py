#   Copyright 2015,2016 Ufora Inc.
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

class GpuFeatureTestCases:

    def test_closure(self):
        captureExpr = """
                let capT = (3s32, 4s64, 5s32);
                let cap64 = 9s64;
                let vec = [1, 2, 3]
                """
        functionExpr = """
                fun(ct) {
                let res = 0
                let x = 0
                while (x < ct)
                    {
                    x = x + 1
                    res = res + x + cap64 + capT[0] + capT[1] + capT[2]
                    }
                res
                }"""
        self.compareCudaToCPU(functionExpr, "[1]", captureExpr)

    def test_read_tuples(self):
        self.compareCudaToCPU("fun((a,b)) { (b,a) }", "[(1,2)]")
        self.compareCudaToCPU("fun((a,b)) { b + a }", "[(1,2)]")
        self.compareCudaToCPU("fun((a,b)) { b + a }", "[(1s32,2s32)]")
        self.compareCudaToCPU("fun(b) { b + 1s32 }", "[2]")
        self.compareCudaToCPU("math.log", "[2]")

    def test_tuple_alignment(self):
        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "[(1s32,2,2s32)]")
        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "[(1u32,2,2s32)]")
        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "[(1u16,2s32,2)]")
        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "[(10.0f32, 2.0, 2)]")
        self.compareCudaToCPU(
                "fun((a,b,c,d,e,f)) { a+b+c+d+e+f }",
                "[(2u16, 3s32, 4s64, 5.0f16, 6.0f32, 7.0f64)]"
                )

    def test_return_or_throw(self):
        functionExpr = """
            fun(x) {
                if (x>0)
                    x
                else
                    throw "x <= 0"
            }
            """
        self.compareCudaToCPU(functionExpr, "[1]", "")
        self.checkCudaRaises(functionExpr, "[0]", "")

    def test_throw(self):
        functionExpr = """
            fun(x) {
                throw "x <= 0"
            }
            """
        self.checkCudaRaises(functionExpr, "[0]", "")
        self.checkCudaRaises(functionExpr, "[1]", "")

    def test_conversions(self):
        s_integers = ["2s16", "3s32", "4s64", "5"]
        u_integers = ["2u16", "3u32", "4u64"]
        floats = ["2.2f32", "3.3f64", "4.4"]

        numbers = s_integers + u_integers + floats
        for n1 in numbers:
            for n2 in numbers:
                for op in ["+", "-", "*" ]:    # TODO: add division, currently broken
                    self.compareCudaToCPU(
                            "fun((a,b)) { a " + op + " b }",
                            "[(" + n1 + ", " + n2 + ")]"
                            )

    def test_two_return_types(self):
        functionExpr = """
            fun(x) {
                let r = if (x < 5) 1.0*x
                else 1 * x;
                r
            }
            """
        self.compareCudaToCPU(functionExpr, "[0]", "")
        self.compareCudaToCPU(functionExpr, "[5]", "")
        self.compareCudaToCPU(functionExpr, "[0, 5, 1, 6, 2, 7, 3, 8, 4, 9]", "")

    def test_three_return_types(self):
        functionExpr = """
            fun(x) {
                let r = if (x < 5) 1.0*x
                else 1 * x;
                if (x > 0) r
                else (0, x)
            }
            """
        self.compareCudaToCPU(functionExpr, "[0]", "")
        self.compareCudaToCPU(functionExpr, "[5]", "")
        self.compareCudaToCPU(functionExpr, "[0, 5, 1, 6, 2, 7, 3, 8, 4, 9]", "")

    def test_too_many_return_types(self):
        functionExpr = """
            fun(x) {
                let r = x;
                for i in sequence (0, x) {
                    r = (0, r)
                    }
                r
            }
            """
        self.checkCudaRaises(functionExpr, "[5]", "")
        self.checkCudaRaises(functionExpr, "[0, 5, 1, 6, 2, 7, 3, 8, 4, 9]", "")

    @unittest.skip
    def test_many_return_types(self):
        functionExpr = """
            fun(0) {(0)}
               (1) {(0,1)}
               (2) {(0,1,2)}
               (3) {(0,1,2,3)}
               (...) { (0,1,2,3,4)}
            """
        self.compareCudaToCPU(functionExpr, "[0]", "")
        self.compareCudaToCPU(functionExpr, "[2]", "")
        self.compareCudaToCPU(functionExpr, "[3]", "")
        self.compareCudaToCPU(functionExpr, "[4]", "")
        self.compareCudaToCPU(functionExpr, "[0, 5, 1, 6, 2, 7, 3, 8, 4, 9]", "")

    @unittest.skip
    def test_return_nothing(self):
        functionExpr = """
            fun(x) {()}
            """
        self.compareCudaToCPU(functionExpr, "[5]", "")
        self.compareCudaToCPU(functionExpr, "[0, 5, 1, 6, 2, 7, 3, 8, 4, 9]", "")

    @unittest.skip
    def test_two_return_types_1(self):
        functionExpr = """
            fun(x) {
                if (x > 0)
                    return 1
                else
                    return 1.0
            }
            """
        self.compareCudaToCPU(functionExpr, "[0]", "")
        self.compareCudaToCPU(functionExpr, "[1]", "")

    @unittest.skip
    def test_return_constant(self):
        functionExpr = """
            fun(x) {
                0
            }
            """
        self.compareCudaToCPU(functionExpr, "[0]", "")
        self.compareCudaToCPU(functionExpr, "[1]", "")
        self.compareCudaToCPU(functionExpr, "[11]", "")
        self.compareCudaToCPU(functionExpr, "[101]", "")

    def test_division(self):
        functionExpr = """
            fun(x) {
                if (x > 0.0)
                    1.0 / x
                else
                    0 * x
            }
            """
        self.compareCudaToCPU(functionExpr, "[0.0, 1.0, 2.0]", "")
        self.compareCudaToCPU(functionExpr, "[0.0]", "")
        self.compareCudaToCPU(functionExpr, "[1.0]", "")
