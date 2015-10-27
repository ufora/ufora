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

import ufora.native.SharedState as SharedStateNative

RandomGenerator = SharedStateNative.RandomGenerator

class RandomGeneratorTest(unittest.TestCase):
    def assertGeneratorsDoSameThing(self, gen1, gen2):
        sequence1 = [gen1.rand() for _ in range(100)]
        sequence2 = [gen2.rand() for _ in range(100)]

        self.assertEqual(sequence1, sequence2)

    def assertGeneratorsAreDifferent(self, gen1, gen2):
        sequence1 = [gen1.rand() for _ in range(100)]
        sequence2 = [gen2.rand() for _ in range(100)]

        self.assertFalse(set(sequence1).intersection(set(sequence2)))

    def test_sequential_pulls_not_equal(self):
        gen = RandomGenerator('hello')

        x = set([gen.rand() for _ in range(100)])

        self.assertEqual(len(x), 100)

    def test_same_seeds_produce_same_values(self):
        gen1 = RandomGenerator('hello')
        gen2 = RandomGenerator('hello')

        self.assertTrue(gen1.rand() == gen2.rand())
        self.assertGeneratorsDoSameThing(gen1, gen2)

        gen3 = gen1.newGenerator()
        gen4 = gen2.newGenerator()

        self.assertGeneratorsDoSameThing(gen3, gen4)

    def test_different_seeds_produce_different_vals(self):
        gen1 = RandomGenerator("gen1")
        gen2 = RandomGenerator("gen2")

        self.assertGeneratorsAreDifferent(gen1, gen2)
        self.assertGeneratorsAreDifferent(gen1.newGenerator(), gen2.newGenerator())

