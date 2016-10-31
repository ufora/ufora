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

_evaluator = None

def evaluator():
    # NOTE here we are setting it automatically but we ought to require an
    # explicit setup here
    global _evaluator
    if _evaluator is None:
        assert False, "Evaluator module not initialized. Please call Evaluator.initialize()"
    return _evaluator

def swapEvaluator(newEvaluator):
    """Swap out the evaluator. returns the old one, so it can be put back later"""
    global _evaluator
    oldEval = _evaluator
    _evaluator = newEvaluator
    return oldEval

def initialize(setupObjectToUse=None, useLocalEvaluator=True, vdmOverride=None):
    global _evaluator

    if _evaluator is not None:
        return

    import ufora.FORA.python.Evaluator.LocalEvaluator as LocalEvaluator
    import ufora.FORA.python.Evaluator.CumulusEvaluator as CumulusEvaluator

    if setupObjectToUse is None:
        configToUse = Setup.config()
    else:
        configToUse = setupObjectToUse.config

    if useLocalEvaluator:
        _evaluator = LocalEvaluator.defaultLocalEvaluator(vdmOverride=vdmOverride)
    else:
        import ufora.native.CallbackScheduler as CallbackSchedulerNative
        schedulerFactory = CallbackSchedulerNative.createSimpleCallbackSchedulerFactory()
        _evaluator = CumulusEvaluator.CumulusEvaluator(
            schedulerFactory.createScheduler("CumulusEvaluator", 1)
            )

def isInitialized():
    global _evaluator
    return _evaluator is not None


