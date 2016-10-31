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

"""
Future

Wraps the result to an asynchronous computation
"""

import time
import logging
import traceback
import concurrent.futures._base as Futures

KEYBOARD_INTERRUPT_WAKEUP_INTERVAL = 0.01

class Future(Futures.Future):
    """
    This pyfora.Future object subclasses the standard Python
    concurrent.futures._base.Future object. See:
    http://pythonhosted.org/futures/
    https://pypi.python.org/pypi/futures

    Futures wrap the result to an asynchronous computation which can
    be accessed by a blocking call to :func:`~pyfora.Future.Future.result`.

    The pyfora Future object extends the concurrent.futures object by
    supporting cancellation with the :func:`~pyfora.Future.Future.cancel` method.
    """
    def __init__(self, onCancel=None):
        super(Future, self).__init__()
        self._computedValue = None
        self._onCancel = onCancel


    def cancel(self):
        """Cancel a running computation"""
        if super(Future, self).cancel():
            return True

        with self._condition:
            if self._state is not Futures.RUNNING or self._onCancel is None:
                # can't cancel
                return False
            if self._onCancel(self._computedValue):
                self._state = Futures.CANCELLED
                self._condition.notify_all()

        self._invoke_callbacks()
        return True

    def setComputedValue(self, computedValue):
        ''' Should only be called by Executor '''
        self._computedValue = computedValue

    def resultWithWakeup(self, statusUpdateFunction=None):
        """Poll the future, but wake up frequently (to allow for keyboard interrupts)."""
        hasSubscribed = [False]
        timeOfLastSubscription = [time.time()]
        isComplete = [False]

        try:
            while True:
                try:
                    if (statusUpdateFunction is not None and 
                            self._computedValue is not None and 
                            hasSubscribed[0] == False and 
                            time.time() > timeOfLastSubscription[0] + 1.0):
                        hasSubscribed[0] = True
                        def onSuccess(result):
                            hasSubscribed[0] = False
                            timeOfLastSubscription[0] = time.time()
                            if not isComplete[0]:
                                try:
                                    statusUpdateFunction(result)
                                except:
                                    logging.error("statusUpdateFunction threw an unexpected exception:\n%s", traceback.format_exc())

                        def onFailure(result):
                            logging.error("subscribing to computation statistics produced unexpected error: %s", result)
                            hasSubscribed[0] = False
                            timeOfLastSubscription[0] = time.time()

                        self._computedValue.get_stats({'onSuccess': onSuccess, 'onFailure': onFailure})
                        timeOfLastSubscription[0] = time.time()

                    return self.result(timeout=KEYBOARD_INTERRUPT_WAKEUP_INTERVAL)
                except Futures.TimeoutError:
                    pass
        finally:
            isComplete[0] = True
            if statusUpdateFunction is not None:
                statusUpdateFunction(None)

