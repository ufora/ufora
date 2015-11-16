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

import concurrent.futures._base as Futures

KEYBOARD_INTERRUPT_WAKEUP_INTERVAL = 0.01

class Future(Futures.Future):
    """
    This pyfora.Future object subclasses the standard Python
    concurrent.futures._base.Future object. See:
    http://pythonhosted.org/futures/
    https://pypi.python.org/pypi/futures

    Futures wrap the result to an asynchronous computation which can
    be accessed by a blocking call to :func:`result`.

    The pyfora Future object extends the concurrent.futures object by
    supporting cancellation with the :func:`cancel` method.
    """
    def __init__(self, executorState=None, onCancel=None):
        super(Future, self).__init__()
        self._executorState = executorState
        self._onCancel = onCancel


    def cancel(self):
        """Cancel a running computation"""
        if super(Future, self).cancel():
            return True

        with self._condition:
            if self._state is not Futures.RUNNING or self._onCancel is None:
                # can't cancel
                return False
            if self._onCancel(self._executorState):
                self._state = Futures.CANCELLED
                self._condition.notify_all()

        self._invoke_callbacks()
        return True

    def setExecutorState(self, state):
        ''' Should only be called by Executor '''
        self._executorState = state

    def resultWithWakeup(self):
        """Poll the future, but wake up frequently (to allow for keyboard interrupts)."""
        while True:
            try:
                return self.result(timeout=KEYBOARD_INTERRUPT_WAKEUP_INTERVAL)
            except Futures.TimeoutError:
                pass
