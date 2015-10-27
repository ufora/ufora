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
import ufora.native.Json as Json
import ufora.core.SubprocessRunner as SubprocessRunner

class SubprocessRunnerTest(unittest.TestCase):
    def test_subprocess_runner_runner(self):
        err = []
        out = []

        runner = SubprocessRunner.SubprocessRunner(
            ["/bin/echo", "asdf"],
            out.append,
            err.append
            )

        runner.start()
        self.assertEqual(runner.wait(10), 0)
        self.assertEqual(out, ["asdf"])
        self.assertEqual(err, [])
        runner.stop()

    def test_subprocess_runner_exception(self):
        err = []
        out = []

        runner = SubprocessRunner.SubprocessRunner(
            ["/bin/bash", "-c", "echo toErr 1>&2; echo toNormal"],
            out.append,
            err.append
            )

        runner.start()
        self.assertEqual(runner.wait(10), 0)
        self.assertEqual(out, ['toNormal'])
        self.assertEqual(err, ["toErr"])
        runner.stop()

