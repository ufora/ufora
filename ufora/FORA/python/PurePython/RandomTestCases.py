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


import pyfora.random.mtrand as mtrand


class RandomTestCases(object):
    # All test cases were checked against our pure fora implementation

    def test_random_1(self):
        def f():
            randomState = mtrand.RandomState(seed=42)
            return randomState.rand()[0]

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            0.374540114455
            )

    def test_random_2(self):
        def f():
            randomState = mtrand.RandomState(seed=42)
            return randomState.rand(size=10)[0]

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            [0.374540114455265, 0.796542984248013, 0.950714311573954,
             0.183434787862134, 0.731993938392961, 0.779690997493525,
             0.598658486362859, 0.596850161534536, 0.156018638714212,
             0.445832757641135]
            )

    def test_random_repeated_sampling(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            rand0, randomstate = randomstate.rand()
            rand1, randomstate = randomstate.rand()
            rand2, randomstate = randomstate.rand()

            return (rand0, rand1, rand2)

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            [0.374540114455265, 0.796542984248013, 0.950714311573954]
            )
            
    def test_random_normals_1(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            return randomstate.randn()[0]

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            -0.5169641645916238
            )

    def test_random_normals_2(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            return randomstate.randn(size=10)[0]

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            [-0.516964164591624, 1.22192121769965, 0.72133261293396,
             0.869635816494383, 1.61821688335969, 1.58855636579379,
             -1.1883085747175, -0.18712466955546, -0.687744403045732,
             -0.0634200268086033]
            )

    def test_random_normals_3(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            _, randomstate = randomstate.randn()
            return randomstate.randn(size=9)[0]

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            [1.22192121769965, 0.72133261293396, 0.869635816494383,
             1.61821688335969, 1.58855636579379, -1.1883085747175,
             -0.18712466955546, -0.687744403045732, -0.0634200268086033]
            )

    def test_various_randoms(self):
        def f():
            rng = mtrand.RandomState(seed=42)
            f, rng = rng.rand(4)
            p, rng = rng.rand()

            return p + f[0]

        # just check that this doesn't blow up
        self.evaluateWithExecutor(f)

    def test_random_uniforms_1(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            unif, _ = randomstate.uniform(-1, 1)
            return unif

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            -0.250919771089
            )

    def test_random_uniforms_2(self):
        def f():
            randomstate = mtrand.RandomState(seed=42)
            return randomstate.uniform(low=-1.0, high=1.0, size=9)[0]

        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f),
            [-0.25091977108947, 0.593085968496025, 0.901428623147908,
             -0.633130424275731, 0.463987876785922, 0.55938199498705,
             0.197316972725718, 0.193700323069072, -0.687962722571575]
            )
