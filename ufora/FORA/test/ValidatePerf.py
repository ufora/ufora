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

import ufora.config.Setup as Setup
import ufora.FORA.python.FORA as FORA
import ufora.FORA.test as FORATestModule

import sys
import os
import logging
import time
import numpy as np

testPath = os.path.split(FORATestModule.__file__)[0]

def evalTimingsForModuleMember(filename, memberName, callResult = False):
    foraModule = FORA.importModule(os.path.join(testPath, filename))
    
    if callResult:
        toCall = getattr(foraModule, memberName)
        evalFun = lambda n: FORA.eval(
            "toCall()",
            locals = { 'toCall' : toCall },
            parsePath = ["LocalPerfTestRunner"]
            )
    else:
        evalFun = lambda n: FORA.eval(
            "foraModule.%s" % memberName,
            locals = { 'foraModule' : foraModule },
            parsePath = ["LocalPerfTestRunner"]
            )

    measureTimingsInLoop(evalFun)

def evalTimingsForExpr(expression, callResult = False):
    if callResult:
        toCall = FORA.eval(expression)
        evalFun = lambda n: FORA.eval(
            "toCall()",
            locals = { "toCall" : toCall },
            parsePath = ["LocalPerfTestRunner"]
            )
    else:
        evalFun = lambda n: FORA.eval(
            expression, parsePath = ["LocalPerfTestRunner"]
            )

    measureTimingsInLoop(evalFun)

def measureTimingsInLoop(evalFun):
    timings = []
    totalAttempts = 0

    while True:
        totalAttempts += 1

        if totalAttempts > 100:
            print "1000.0"
            return

        t0 = time.time()
        evalFun(totalAttempts)
        timings.append(time.time() - t0)

        if len(timings) > 20:
            timings = timings[len(timings) - 20:]

        #see if the timings have stabilized by checking whether the lowest and third lowest
        #are within 5% of each other
        if len(timings) > 10:
            st = sorted(timings)
            if (st[2] - st[0]) / st[0] < 0.05:
                print st[0]
                return


def main(argv):
    """
    expects arguments of the form: 
    (1) sys.argv = [__file__, foraExpr, 
                       <"callResult">]
        for single fora expressions, or
    (2) sys.argv = [__file__, foraFileName, moduleMemberName, "moduleMember", <"callResult">]
        for accessing a module member in a file
    """
    callResult = "callResult" in sys.argv

    if "moduleMember" in sys.argv:
        evalTimingsForModuleMember(
            filename = sys.argv[1], memberName = sys.argv[2], 
            callResult = callResult
            )
    else:
        evalTimingsForExpr(
            expression = sys.argv[1], callResult = callResult
            )

    return 0

if __name__ == "__main__":
    try:
        setup = Setup.defaultSetup()
        setup.config.configureLogging(logging.WARN)

        import ufora.FORA.python.Evaluator.LocalEvaluator as LocalEvaluator
        LocalEvaluator.DISABLE_SPLITTING = True

        with Setup.PushSetup(setup):
            FORA.initialize()

        resultCode = main(sys.argv)
    except:
        import traceback
        print >> sys.stderr, traceback.format_exc()
        resultCode = 255

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(resultCode)

