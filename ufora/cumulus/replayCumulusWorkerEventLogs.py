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
import logging
import ufora.config.Setup as Setup
import ufora.native.FORA as ForaNative
import ufora.native.Cumulus as CumulusNative
import ufora.FORA.python.FORA as FORA
import cPickle as pickle
import ufora.config.Mainline as Mainline
import sys

def main(parsedArguments):
    try:
        eventSets = pickle.load(open(parsedArguments.file, "r"))
    except:
        eventSets = None

    if eventSets is not None:
        for events in eventSets:
            logging.warn("**********************************************")
            if len(events):
                logging.warn("validating %s", events[0])
            logging.warn("")

            CumulusNative.replayCumulusWorkerEventStream(events, parsedArguments.validation)
    else:
        CumulusNative.replayCumulusWorkerEventStreamFromFile(
            parsedArguments.file, 
            parsedArguments.validation
            )

    return 0


def createParser():
    desc = """Utility for validating a stream of LocalSchedulerEvent objects in a test failure. """
    parser = Setup.defaultParser(
            description = desc
            )
    parser.add_argument(
        'file',
        help='names of file to be read'
        )
    parser.add_argument(
        '-n',
        '--no_validation',
        dest='validation',
        action='store_false',
        default=True,
        required=False,
        help="don't validate the response stream"
        )

    return parser


if __name__ == "__main__":
    Mainline.UserFacingMainline(
        main,
        sys.argv,
        modulesToInitialize = [],
        parser = createParser()
        )


