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

#!/usr/bin/python
import time
import logging
import ufora.config.Setup as Setup
import ufora.native.FORA as ForaNative
import ufora.native.Cumulus as CumulusNative
import ufora.FORA.python.FORA as FORA
import cPickle as pickle
import ufora.config.Mainline as Mainline
import sys
import argparse

def formatTimestamp(timestamp):
    return time.strftime("%a, %d %b %Y %H:%M:%S +", time.gmtime(timestamp)) + ".%05d" % int((timestamp % 1.0) * 100000)

def extractMachineIdFromEvent(event):
    eventStr = str(event)

    if "Machine((" not in eventStr:
        return None

    ix = eventStr.index("Machine((")

    return eventStr[ix+9:ix+17]

def extractEventSets(parsedArguments):
    if len(parsedArguments.files) == 1 and 'scheduler_events' in parsedArguments.files[0]:
        return pickle.load(open(parsedArguments.files[0],"r"))
    else:
        result = []

        for filename in parsedArguments.files:
            result.append(
                CumulusNative.extractCumulusWorkerEventsFromFile(filename)
                )

        return result

def summarize(filenames):
    for filename in filenames:
        print "*********************************************************************************"
        print filename
        print "*********************************************************************************"

        events = CumulusNative.extractCumulusWorkerEventsFromFile(filename)

        print events[0]
        print "timestamps: ", events[0].timestamp, events[-1].timestamp
        print "timestamps: ", formatTimestamp(events[0].timestamp), formatTimestamp(events[-1].timestamp)
        print
        print

def printDetails(parsedArguments, shouldDump):
    allEventsByTimestampAndMachineId = []

    eventSets = extractEventSets(parsedArguments)

    for events in eventSets:
        machineId = extractMachineIdFromEvent(events[0])

        for e in events:
            if shouldDump(e):
                allEventsByTimestampAndMachineId.append(
                    (e.timestamp, machineId, e)
                    )


    allEventsByTimestampAndMachineId = sorted(allEventsByTimestampAndMachineId)

    print
    print
    print

    for timestamp, machineId, event in allEventsByTimestampAndMachineId:
        eventAsString = str(event)
        lines = eventAsString.split("\n")

        preamble = machineId + "   %.3f" % (timestamp % 1000.0)

        if len(preamble) < 30:
            preamble = preamble + " " * (30 - len(preamble))

        lines[0] = preamble + lines[0]
        lines[1:] = [" " * 30 + l for l in lines[1:]]

        print "\n".join(lines)
        print


class Filter:
    def __init__(self, parsedArguments):
        self.timestamps = parsedArguments.timestamps
        self.exclusions = parsedArguments.exclusions
        self.inclusions = parsedArguments.inclusions
        self.state_changes_only = parsedArguments.state_changes_only
        self.currentComputationStates = {}

    def __call__(self, event):
        if not self.keepStateChangeEvent(event):
            if self.state_changes_only:
                return False

        if self.timestamps:
            if event.timestamp < self.timestamps[0]:
                return False
            if event.timestamp > self.timestamps[1]:
                return False

        msg = str(event)

        if self.exclusions:
            for e in self.exclusions:
                if e in msg:
                    return False

        if not self.inclusions:
            return True

        for i in self.inclusions:
            if i in msg:
                return True
        return False

    def keepStateChangeEvent(self, event):
        if not event.isActiveComputations():
            return False

        activeCompEvent = event.asActiveComputations.event

        if not activeCompEvent.isInternal_GetComputationStatus():
            return False

        comp = activeCompEvent.asInternal_GetComputationStatus.computation
        status = activeCompEvent.asInternal_GetComputationStatus.status

        if comp not in self.currentComputationStates or self.currentComputationStates[comp] != status:
            self.currentComputationStates[comp] = status
            return True

        return False

    def summarize(self):
        #show all computations that depend on finished computations
        for comp, finalStatus in self.currentComputationStates.iteritems():
            if finalStatus.isBlockedOnComputations():
                subcomps = [x for x in finalStatus.asBlockedOnComputations.subthreads]
                for s in subcomps:
                    if s not in self.currentComputationStates:
                        print "ERROR: %s depends on %s which we never saw change state." % (comp, s)
                    elif self.currentComputationStates[s].isFinished():
                        print "ERROR: %s depends on %s which was finished!" % (comp, s)

    
def main(parsedArguments):
    if parsedArguments.summarize:
        summarize(parsedArguments.files)
    else:
        eventFilter = Filter(parsedArguments)

        printDetails(parsedArguments, eventFilter)
        
        eventFilter.summarize()
    return 0


def createParser():
    desc = """Read a stream of CumulusWorkerEvent objects and print them"""
    epilog = """
Example:

    python extractCumulusWorkerEventLogs.py **/CumulusServiceEvents.*.log \\
                --ts 1398362678.66 1398362703.98 \\
                --exclusions SplitOrMoveIfNeeded Priority \\
                --inclusions 866DEDC48E92 1A255CBEF9E1 WorkerReadyToCompute

will dump all logs below the current directory, with timestamps between the given bounds,
and with inclusions and exclusions given
"""
    parser = Setup.defaultParser(
            minimalParser = True,
            description = desc,
            epilog = epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter
            )
    
    parser.add_argument(
        '--summarize',
        help='only summarize',
        default=False,
        action='store_true'
        )

    parser.add_argument(
        '--state-changes-only',
        help='only show state-changes of computations',
        default=False,
        action='store_true',
        dest='state_changes_only'
        )

    parser.add_argument(
        '--ts',
        help='timestamp range as a pair of floats',
        dest='timestamps',
        default=None,
        type=float,
        nargs=2,
        action='store'
        )

    parser.add_argument(
        'files',
        help='files to read',
        nargs='*'
        )

    parser.add_argument(
        '--inclusions',
        nargs='*',
        help='strings to search for and include in log messages'
        )

    parser.add_argument(
        '--exclusions',
        nargs='*',
        help='strings to search for and exclude from log messages'
        )
    return parser


if __name__ == "__main__":
    Mainline.UserFacingMainline(
        main,
        sys.argv,
        modulesToInitialize = [],
        parser = createParser()
        )


