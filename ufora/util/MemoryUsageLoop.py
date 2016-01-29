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
import os
import threading
import resource
import ufora.util.ManagedThread as ManagedThread

def memoryWriteLoop(logfileLocation, interval):
    try:
        if isinstance(logfileLocation, file):
            outputFile = logfileLocation
        else:
            outputFile = open(logfileLocation, "w", 0) 

        def pad(s, finalLength):
            return s + " " * (finalLength - len(s))

        def formatCols(columns):
            return "".join([pad(columns[0],30)] + [pad(c, 15) for c in columns[1:]])

        columns = ["timestamp", "total size MB", "RSS MB", "shared MB", "code MB", "stack MB", "library MB", "dirty MB"]

        print >> outputFile, formatCols(columns)
        while True:
            with open("/proc/%s/statm" % os.getpid(), "r") as f:
                data = ["%.2f" % (int(x) * resource.getpagesize() / 1024 / 1024.0) for x in f.readline().split(" ")]

            print >> outputFile, formatCols([time.strftime("%Y-%m-%dT%H:%M:%S")] + data)

            time.sleep(interval)
    except:
        import traceback
        traceback.format_exc()

started = False
def startLoop(logfileLocation, interval = 1.0):
    global started
    if started:
        return
    started = True

    t = ManagedThread.ManagedThread(target = memoryWriteLoop, args = (logfileLocation,interval))
    t.daemon = True
    t.start()

