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
import pyfora
import scipy.linalg


class ScipyLinalgTestCases(object):
    def test_expm_1(self):
        x = numpy.array([[1,3],[2,4]])

        def f():
            return scipy.linalg.expm(x)

        numpy.testing.assert_allclose(
            f(),
            self.evaluateWithExecutor(f)
            )

    def test_expm_2(self):
        x = numpy.array([[0, 1], [-1, 0]])

        def f():
            return scipy.linalg.expm(x)

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, ValueError)
