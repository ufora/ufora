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

    def test_closure(self):
        captureExpr = """
                let capT = (3s32, 4s64, 5s32);
                let cap64 = 9s64;
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
        self.compareCudaToCPU(functionExpr, "[0]", captureExpr)
        self.compareCudaToCPU(functionExpr, "[1]", captureExpr)
        self.compareCudaToCPU(functionExpr, "[1, 3, 100]", captureExpr)

    def test_closure_vec_int(self):
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
                    res = res + x + cap64 + capT[0] + capT[1] + capT[2] + vec[0]
                    }
                res
                }"""
        self.compareCudaToCPU(functionExpr, "[0]", captureExpr)
        self.compareCudaToCPU(functionExpr, "[1]", captureExpr)
        self.compareCudaToCPU(functionExpr, "[1, 3, 100]", captureExpr)

    def test_closure_vec_float(self):
        captureExpr = """
                let capT = (3s32, 4s64, 5s32);
                let cap64 = 9s64;
                let vec = [1.0, 2.5, 3.9]
                """
        functionExpr = """
                fun(ct) {
                let res = 0.0;
                let x = 0;
                while (x < ct)
                    {
                    x = x + 1
                    res = res + x + cap64 + capT[0] + capT[1] + capT[2] + vec[0]
                    };
                res
                }"""
        self.compareCudaToCPU(functionExpr, "[0]", captureExpr)
        self.compareCudaToCPU(functionExpr, "[1]", captureExpr)
        self.compareCudaToCPU(functionExpr, "[1, 3, 100]", captureExpr)

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

    def test_return_or_unsupported(self):
        functionExpr = """
            fun(x) {
                if (x>0)
                    x
                else
                    String(x) + "a"
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

    def test_two_return_types_const(self):
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

    def test_return_constant_1(self):
        functionExpr = """
            fun(x) {
                0
            }
            """
        self.compareCudaToCPU(functionExpr, "[0]", "")
        self.compareCudaToCPU(functionExpr, "[1]", "")
        self.compareCudaToCPU(functionExpr, "[11]", "")
        self.compareCudaToCPU(functionExpr, "[101]", "")

    def test_return_constant_2(self):
        functionExpr = """
                fun(x) {
                    if (x < 5) 1 else 0
                }
                """
        vectorExpr = "Vector.range(10)"

        self.compareCudaToCPU(functionExpr, vectorExpr)

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

    def test_two_vec_multiply(self):
        captureExpr = """
                let vec_len = 20;
                let vec1 = Vector.range(vec_len, fun(y){y});
                let vec2 = Vector.range(vec_len, fun(z){z});
                """
        functionExpr = """
                fun(x) {
                vec1[x] * vec2[x];
                }"""
        vectorExpr = "Vector.range(vec_len)"
        print "CapEx: ", captureExpr
        self.compareCudaToCPU(functionExpr, vectorExpr, captureExpr)

    def test_flat_mat_add_unrolled_conversions(self):
        captureExpr = """
                let mat_d = 30;
                let mat1 = Vector.range(mat_d * mat_d);
                let mat2 = Vector.range(mat_d * mat_d);
                """
        functionExpr = """
                fun(xy) {
                    let offset = xy[0] * mat_d + xy[1];
                    mat1[offset] + mat2[offset]
                }"""

        vectorExpr = "Vector.range(mat_d * mat_d, fun(offset) { (offset / mat_d, offset % mat_d) })"

        self.compareCudaToCPU(functionExpr, vectorExpr, captureExpr)

    def test_flat_mat_add(self):
        captureExpr = """
                let mat_d = 20
                let convert_1d2d = fun(offset) { (offset / mat_d, offset % mat_d)};
                let convert_2d1d = fun(xy) { xy[0] * mat_d + xy[1]};
                let mat1 = Vector.range(mat_d * mat_d);
                let mat2 = Vector.range(mat_d * mat_d);
                """
        functionExpr = """
                fun(xy) {
                let offset = convert_2d1d(xy)
                mat1[offset] + mat2[offset]
                }"""
        vectorExpr = "Vector.range(mat_d * mat_d, fun(offset) { convert_1d2d(offset) })"

        self.compareCudaToCPU(functionExpr, vectorExpr, captureExpr)

    def test_flat_mat_mult_unrolled_conversions(self):
        captureExpr = """
                let mat_d = 20;
                let mat1 = Vector.range(mat_d * mat_d);
                let mat2 = Vector.range(mat_d * mat_d);
                """
        functionExpr = """
                fun(xy) {
                let sum = 0;
                let k = 0;
                 while (k < mat_d) {
                   let prod = mat1[xy[0] * mat_d + k] * mat2[k * mat_d + xy[1]];
                   sum = sum + prod;
                   k = k + 1
                   }
                 sum
                }"""
        vectorExpr = "Vector.range(mat_d * mat_d, fun(offset) { (offset / mat_d, offset % mat_d) })"

        self.compareCudaToCPU(functionExpr, vectorExpr, captureExpr)

    def test_flat_mat_mult(self):
        captureExpr = """
                let mat_d = 20;
                let convert_1d2d = fun(offset) { (offset / mat_d, offset % mat_d)};
                let convert_2d1d = fun(xy) { xy[0] * mat_d + xy[1]};
                let mat1 = Vector.range(mat_d * mat_d);
                let mat2 = Vector.range(mat_d * mat_d);
                """
        functionExpr = """
                fun(xy) {
                let sum = 0;
                let k = 0;
                 while (k < mat_d) {
                   let prod = mat1[convert_2d1d((xy[0], k))] * mat2[convert_2d1d((k, xy[1]))];
                   sum = sum + prod;
                   k = k + 1
                   }
                 sum
                }"""
        vectorExpr = "Vector.range(mat_d * mat_d, fun(offset) { convert_1d2d(offset) })"

        self.compareCudaToCPU(functionExpr, vectorExpr, captureExpr)

    def test_matmult(self):
        dimensionSize = 'let mat_d = 5;'
        captureExpr = '''
                let mat1 = Vector.range(mat_d, fun(x){Vector.range(mat_d, fun(y){(x*mat_d + y) * 1.0})});
                let mat2 = Vector.range(mat_d, fun(x){Vector.range(mat_d, fun(y){(y*mat_d + x) * 1.0})});
                '''
        functionExpr = '''
                fun((x,y)) {
                  let sum = 0;
                  for k in sequence(mat_d) {
                    sum = mat1[x][k] * mat2[k][y]
                  }
                  sum
                }'''

        vectorExpr = '[(x,y) for y in sequence(mat_d) for x in sequence(mat_d)]'

        print "CapEx: ", dimensionSize+captureExpr
        print "FunEx: ", functionExpr
        print "VecEx: ", vectorExpr

        self.compareCudaToCPU(functionExpr, vectorExpr, dimensionSize+captureExpr)

    def test_vec_of_vec_sum(self):
        captureExpr = """
                let mat_d = 20;
                let mat = Vector.range(mat_d, fun(x){Vector.range(mat_d, fun(y){(x*mat_d + y) * 1.0})});
                """
        functionExpr = """
                fun(x) {
                  let sum = 0;
                  for y in sequence(mat_d) {
                    sum = sum + mat[x][y]
                  }
                  sum
                }"""

        vectorExpr = "Vector.range(mat_d)"

        print "CapEx: ", captureExpr
        print "FunEx: ", functionExpr
        print "VecEx: ", vectorExpr

        self.compareCudaToCPU(functionExpr, vectorExpr, captureExpr)
