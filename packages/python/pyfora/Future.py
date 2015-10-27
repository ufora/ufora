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

import concurrent.futures._base as Futures

class Future(Futures.Future):
    '''An implementaion of Future that can hold user-defined state, and may be
    cancellable even from its RUNNING state.
    '''
    def __init__(self, executorState=None, onCancel=None):
        super(Future, self).__init__()
        self._executorState = executorState
        self._onCancel = onCancel


    def cancel(self):
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

