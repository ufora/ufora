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
    """
    represents a seeded Mersenne Twister
    """
    def __init__(self, seed=None, nativeRandomState=None, savedNormal=None):
        if nativeRandomState is None:
            assert seed is not None, "must pass in a seed or a randomState"

            self.nativeRandomState = RandomState.nativeRandomState_(seed)
        else:
            self.nativeRandomState = nativeRandomState

        self.savedNormal = savedNormal

    @staticmethod
    def nativeRandomState_(seed):
        return __inline_fora(
            """fun(@unnamed_args:(seed), *args) {
                   return iterator(math.random.MersenneTwister(seed.@m))
                   }"""
            )(seed)

    def pull_int_(self):
        val, newNativeRandomState = __inline_fora(
            """fun(@unnamed_args:(stateVector), *args) {
                   let intVal = PyInt(pull stateVector);
                   return PyTuple((intVal, stateVector))
                   }"""
            )(self.nativeRandomState)

        return val, RandomState(nativeRandomState=newNativeRandomState)

    def pull_n_ints_(self, n):
        vals, newNativeRandomState = __inline_fora(
            """fun(@unnamed_args:(n, stateVector), *args) {
                   n = n.@m
                   let ix = 0;
                   let vals = [];
                   while (ix < n) {
                       vals = vals :: PyInt(pull stateVector);
                       ix = ix + 1
                       }
                   return PyTuple((PyList(vals), stateVector))
                   }"""
            )(n, self.nativeRandomState)
            
        return vals, RandomState(nativeRandomState=newNativeRandomState)

    def pull_uniform_(self, low=0.0, high=1.0):
        intVal, newRandomState = self.pull_int_()
        val = low + (high - low) * (intVal + 1.0) / (4294967296.0 + 1.0)
        return val, newRandomState

    def pull_n_uniforms_(self, n, low=0.0, high=1.0):
        vals, newNativeRandomState = __inline_fora(
            """fun(@unnamed_args:(n, stateVector, low, high), *args) {
                   n = n.@m
                   low = Float64(low.@m)
                   high = Float64(high.@m)
                   let ix = 0;
                   let vals = [];
                   while (ix < n) {
                       let integerVal = pull stateVector;
                       // 4294967296 = 2 ** 32
                       let floatVal = low + (high - low) * (integerVal + 1.0) / (4294967296.0 + 1.0)
                       vals = vals :: PyFloat(floatVal);
                       ix = ix + 1
                       }
                   return PyTuple((PyList(vals), stateVector))
                   }"""
            )(n, self.nativeRandomState, low, high)
            
        return vals, RandomState(nativeRandomState=newNativeRandomState)        

    def pull_normal_(self):
        if self.savedNormal is not None:
            return self.savedNormal, RandomState(nativeRandomState=self.nativeRandomState)

        normal0, normal1, randomState = self.pull_two_normals_()

        return normal0, RandomState(
            nativeRandomState=randomState.nativeRandomState,
            savedNormal=normal1
            )

    def pull_two_normals_(self):
        randomState = self
        tryIx = 0
        while tryIx < 1000000:
            u, randomState = randomState.pull_uniform_(-1.0, 1.0)
            v, randomState = randomState.pull_uniform_(-1.0, 1.0)
            s = u * u + v * v
            if s <= 1.0 and s != 0.0:
                f = (-2.0 * math.log(s) / s) ** 0.5
                return u * f, v * f, randomState

            tryIx = tryIx + 1
                
        assert False, "too many tries in pull_two_normals_"

    def uniform(self, low=0.0, high=1.0, size=None):
        if size is None:
            return self.pull_uniform_(low=low, high=high)

        return self.pull_n_uniforms_(n=size, low=low, high=high)

    def rand(self, size=None):
        if size is None:
            val, nextRandomState = self.pull_uniform_()
            return val, nextRandomState

        vals, nextRandomState = self.pull_n_uniforms_(n=size)

        return numpy.array(vals), nextRandomState

    def randn(self, size=None):
        if size is None:
            val, nextRandomState = self.pull_normal_()
            return val, nextRandomState

        tr = []
        ix = 0
        randomState = self
        while ix < size:
            val, randomState = randomState.pull_normal_()
            tr = tr + [val]
            ix = ix + 1

        return numpy.array(tr), randomState

    
