#!/usr/bin/env python

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

import signal
import sys
import ufora.config.Mainline as Mainline
import ufora.test.ClusterSimulation as ClusterSimulation

def main(args):
    print "Starting cluster simulation..."
    simulator = ClusterSimulation.Simulator.createGlobalSimulator()
    simulator.startService()

    def signal_handler(sig, _):
        signal_name = '(unknown)'
        if sig == signal.SIGINT:
            signal_name = 'SIGINT'
        elif sig == signal.SIGTERM:
            signal_name = 'SIGTERM'

        print 'Received ', signal_name, 'signal. Exiting.'
        simulator.stopService()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print "Press Ctrl+C to exit."
    signal.pause()


if __name__ == "__main__":
    Mainline.UserFacingMainline(
        main,
        sys.argv,
        modulesToInitialize=[]
        )

