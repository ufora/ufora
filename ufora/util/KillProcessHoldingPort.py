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

import ufora.core.SubprocessRunner as SubprocessRunner
import sys
import re
import os
import logging
import traceback

def pidAndProcessNameHoldingPorts(portStart, portStop):
    output = SubprocessRunner.callAndReturnOutput(
            ["/bin/bash", "-c", "netstat -tulpn 2> /dev/null"],
            timeout = 5
            )

    if output is None:
        #the netstat subprocess must have timed out
        return None

    outputLines = output.split("\n")

    allOutputLinesMatching = []

    for port in range(portStart, portStop):
        for line in output.split("\n"):
            if (":" + str(port)) in line:
                allOutputLinesMatching.append(line)

    if not allOutputLinesMatching:
        return None

    for line in allOutputLinesMatching:
        match = re.match(r'.*LISTEN *([0-9]+)/(.*)', line)

        if match is not None:
            logging.warn("Found process: %s", line)

            pidToKill = int(match.group(1))
            processName = match.group(2)

            return pidToKill, processName

    return None



def killProcessGroupHoldingPorts(portStart, portStop, retries = 5):
    toKillOrNone = pidAndProcessNameHoldingPorts(portStart, portStop)

    if toKillOrNone is None:
        return False

    pidToKill, processName = toKillOrNone

    try:
        pidGroupToKill = os.getpgid(pidToKill)

        logging.warn("Killing process group pgid=%s containing %s at pid=%s",
                pidGroupToKill,
                processName,
                pidToKill
                )

        os.killpg(pidGroupToKill, 9)
    except OSError:
        logging.warn("Failed to kill process holding port: %s.\n%s",
                     toKillOrNone, traceback.format_exc()
                     )

    toKillOrNone2 = pidAndProcessNameHoldingPorts(portStart, portStop)

    if toKillOrNone2 is not None:
        logging.error(
            "Failed to free the port range %s-%s. It was held as %s, now as %s",
            portStart,
            portStop,
            toKillOrNone,
            toKillOrNone2
            )
        if retries < 1:
            raise UserWarning("Failed to clear the port")
        logging.info("Trying to kill process group holding port range %s-%s again", portStart, portStop)
        return killProcessGroupHoldingPorts(portStart, portStop, retries-1)

    return True



if __name__ == '__main__':
    killProcessGroupHoldingPorts(sys.argv[1], sys.argv[2])

