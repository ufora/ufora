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
import ufora.util.StackInfo as StackInfo
import threading


def writeStackTraceSummary(stackLog):
    '''
    Collapse duplicate stack traces...
    '''
    traceDict = {}
    for id, traceList in StackInfo.getTraces().iteritems():
        trace = ''.join(traceList)
        if trace not in traceDict:
            traceDict[trace] = []
        traceDict[trace].append(id)

    for trace, idList in traceDict.iteritems():
        for id in idList:
            stackLog.write(str(id) + '\n')
        stackLog.write("".join(trace))
        stackLog.write('-----------------------------------------------------------------\n')



def stacktraceWriteLoop(logfileLocation, timeout = 20):
    while True:
        time.sleep(timeout)
        with open(logfileLocation, 'w') as stackLog:
            writeStackTraceSummary(stackLog)


def startLoop(logfileLocation, timeout = 20):
    t = threading.Thread(target = stacktraceWriteLoop, args = (logfileLocation,timeout))
    t.daemon = True
    t.start()

