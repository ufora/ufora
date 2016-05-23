#   Copyright 2016 Ufora Inc.
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


import math
import numpy


class RandomState(object):
    def __init__(self, seed=None):
        assert seed is not None, "must pass in a seed"

        self.savedNormalPtr = __inline_fora(
            """fun(*args) {
                   MutableVector(Float64).create(1, 0.0)
                   }"""
            )()
        
        self.hasSavedNormalPtr = __inline_fora(
            """fun(*args) {
                   MutableVector(Bool).create(1, false)
                   }"""
            )()
        
        self.indexPtr = __inline_fora(
            """fun(*args) {
                   MutableVector(UInt32).create(1, 624u32)
                   }"""
            )()
        self.stateVector = __inline_fora(
            """fun(@unnamed_args:(seed), *args) {
                   seed = UInt32(seed.@m)
                   if (seed < 0)
                       throw ValueError(PyString("seeds must be non-negative"))

                   let stateVector = MutableVector(UInt32).create(624, 0u32);
                   stateVector[0] = seed;

                   let ix = 0u32;
                   while (ix < 623u32) {
                       seed = 1812433253u32 * (stateVector[ix] ^ (stateVector[ix] >> 30u32)) + ix + 1u32;
                       ix = ix + 1u32
                       stateVector[ix] = seed
                       }

                   return stateVector
                   }"""
            )(seed)


    def pull_int_(self):
        return __inline_fora(
            """fun(@unnamed_args:(indexPtr, stateVector), *args) {
                   let twist = fun() {
                       let lookup = fun(ix) {
                           if (ix < 624u32)
                               return stateVector[ix]

                           return stateVector[ix - 624u32]
                           }

                       let ix = 0u32;
                       while (ix < 624u32) {
                           let xL = lookup(ix + 1) & 2147483647u32
                           let xU = stateVector[ix] & 2147483648u32
                           let y = (xL | xU);

                           if (y % 2u32 == 1u32)
                               y = (y >> 1u32) ^ 2567483615u32
                           else
                               y = (y >> 1u32)


                           stateVector[ix] = lookup(ix + 397u32) ^ y

                           ix = ix + 1u32
                           }

                       indexPtr[0] = 0u32
                       stateVector
                       }

                   if (indexPtr[0] >= 624u32)
                       twist() // modifies indexPtr

                   let index = indexPtr[0]
                   let y = stateVector[index]

                   y = y ^ (y >> 11u32);
                   y = y ^ ((y << 7u32) & 2636928640u32);
                   y = y ^ ((y << 15u32) & 4022730752u32);
                   y = y ^ (y >> 18u32);

                   indexPtr[0] = index + 1u32

                   return PyInt(y);
                   }"""
            )(self.indexPtr, self.stateVector)
        
    def pull_uniform_(self, low=0.0, high=1.0):
        intVal = self.pull_int_()
        val = low + (high - low) * (intVal + 1.0) / (4294967296.0 + 1.0)
        return val

    def pull_normal_(self):
        if __inline_fora(
                """fun(@unnamed_args:(hasSavedNormalPtr), *args) {
                       PyBool(hasSavedNormalPtr[0])
                       }"""
                )(self.hasSavedNormalPtr):
            tr = __inline_fora(
                """fun(@unnamed_args:(savedNormalPtr), *args) {
                       PyFloat(savedNormalPtr[0])
                       }"""
                )(self.savedNormalPtr)
            __inline_fora(
                """fun(@unnamed_args:(hasSavedNormalPtr), *args) {
                       hasSavedNormalPtr[0] = false
                       }"""
                )(self.hasSavedNormalPtr)
            return tr
        
        normal0, normal1 = self.pull_two_normals_()

        __inline_fora(
            """fun(@unnamed_args:(normalToSave, savedNormalPtr), *args) {
                   savedNormalPtr[0] = normalToSave.@m
                   }"""
            )(normal1, self.savedNormalPtr)

        __inline_fora(
            """fun(@unnamed_args:(hasSavedNormalPtr), *args) {
                   hasSavedNormalPtr[0] = true
                   }"""
            )(self.hasSavedNormalPtr)

        return normal0

    def pull_two_normals_(self):
        tryIx = 0
        while tryIx < 1000000:
            u = self.pull_uniform_(-1.0, 1.0)
            v = self.pull_uniform_(-1.0, 1.0)
            s = u * u + v * v
            if s <= 1.0 and s != 0.0:
                f = (-2.0 * math.log(s) / s) ** 0.5
                return u * f, v * f

            tryIx = tryIx + 1
                
        assert False, "too many tries in pull_two_normals_"            

    def rand(self, size=None):
        if size is None:
            return self.pull_uniform_()

        tr = []
        for _ in xrange(size):
            tr = tr + [self.pull_uniform_()]

        return numpy.array(tr)

    def randn(self, size=None):
        if size is None:
            return self.pull_normal_()

        tr = []
        ix = 0
        while ix < size:
            tr = tr + [self.pull_normal_()]
            ix = ix + 1

        return numpy.array(tr)

    def uniform(self, low=0.0, high=1.0, size=None):
        if size is None:
            return self.pull_uniform_(low=low, high=high)

        tr = []
        ix = 0
        while ix < size:
            tr = tr + [self.pull_uniform_(low=low, high=high)]
            ix = ix + 1

        return numpy.array(tr)

