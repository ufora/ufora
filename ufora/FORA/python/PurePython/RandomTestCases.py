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

import numpy
import numpy.testing


import numpy.random.mtrand as mtrand


class RandomTestCases(object):
    # All test cases were checked against our pure fora implementation

    def test_random_1(self):
        def f():
            randomState = numpy.random.mtrand.RandomState(seed=42)
            return randomState.rand()

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )

    def test_random_2(self):
        def f():
            randomState = mtrand.RandomState(seed=42)
            return randomState.rand(10)

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )

    def test_random_repeated_sampling(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            rand0 = randomstate.rand()
            rand1 = randomstate.rand()
            rand2 = randomstate.rand()

            return (rand0, rand1, rand2)

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )
            
    def test_random_normals_1(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            return randomstate.randn()

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )

    def test_random_normals_2(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            return randomstate.randn(10)

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )

    def test_random_normals_3(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            randomstate.randn()
            return randomstate.randn(9)

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )

    def test_various_randoms(self):
        def f():
            rng = mtrand.RandomState(seed=42)
            f = rng.rand(4)
            p = rng.rand()

            return p + f[0]

        # just check that this doesn't blow up
        self.evaluateWithExecutor(f)

    def test_random_uniforms_1(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            unif = randomstate.uniform(-1, 1)
            return unif

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )

    def test_random_uniforms_2(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            return randomstate.uniform(low=-1.0, high=1.0, size=9)

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            f()
            )

