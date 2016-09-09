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

import ufora.core.SubprocessRunner as SubprocessRunner

def assertPrints(expression, expectedResult):
    returnCode, output, err = SubprocessRunner.callAndReturnResultAndOutput(
        ["fora", "-e", expression ]
        )

    output = [l.strip() for l in output if l.strip()]

    assert returnCode == 0
    assert output == [expectedResult], \
        "Evaluating:\n\t%s\n\nExpected %s, got %s" % (expression, [expectedResult], output)

assertPrints("let v = MutableVector(Float64).create(10,0.0); v[5] = 5.5; String(v[5])", "5.5")
assertPrints("let v = (MutableVector(Float64).create(10,0.0),5.5); v[0][5] = v[1]; String(v[0][5])", "5.5")

