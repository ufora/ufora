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

import time
import traceback
import logging

def retryAssert(assertion, args, numRetries=10, sleepInterval=.1, verbose=False):
    '''Retries an assertion over args numRetries times. It should be
    used for things that will eventually become true instead of sleeping

    assertion       :   an assertion function from unittest.TestCase
    args            :   a list of callables to be called every iteration
                        This is to allow for changing values
    numRetries      :   an integer
    '''

    done = False
    retries = 0
    evaluatedArgs = None
    while not done:
        try:
            evaluatedArgs = [x() for x in args]
            if verbose:
                logging.debug('trying to assert %s on %s', assertion, evaluatedArgs)
            assertion(*evaluatedArgs)
            return 
        except Exception as e:
            if retries == numRetries:
                for x in evaluatedArgs:
                    print x
                print "Failed with assertion after %s tries" % numRetries
                raise 
            if verbose:
                logging.debug('retryAssert found exception %s', traceback.format_exc(e))
            retries += 1

            time.sleep(sleepInterval)

def waitUntilTrue(functionToCheck, timeout, sleepInterval = 0.01):
    """Waits for up to 'timeout' seconds for 'functionToCheck' to become True.

    functionToCheck - a callable
    timeout - how many seconds to wait
    sleepInterval - how long to sleep between checks
    """
    t0 = time.time()
    
    while time.time() - t0 < timeout:
        if functionToCheck():
            return True
        time.sleep(sleepInterval)

    return False

