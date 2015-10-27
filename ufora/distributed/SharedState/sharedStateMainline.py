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

import sys
import argparse
import signal
import logging
import ufora.config.Setup as Setup
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.config.Mainline as Mainline





if __name__ == "__main__":
    callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()
    callbackScheduler = callbackSchedulerFactory.createScheduler("sharedStateScheduler", 1)
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokenSigningKey')
    parser.add_argument('--cacheDir')
    parsed, remaining = parser.parse_known_args(sys.argv[1:])




    def startSharedState(args):
        if parsed.cacheDir:
            logging.info("Shared state cache directory: %s", parsed.cacheDir)
            Setup.config().sharedStateCache = parsed.cacheDir

        service = SharedStateService.SharedStateService(callbackScheduler, parsed.tokenSigningKey)

        service.startService()
        service.blockUntilListening()


        def handleSigTerm(signum, frame):
            logging.info("SIGTERM received - shutting down")
            service.stopService()

        signal.signal(signal.SIGTERM, handleSigTerm)

        signal.pause()
        logging.info("process exiting")

    Mainline.UserFacingMainline(startSharedState, [sys.argv[0]] + remaining)



