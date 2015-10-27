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

import argparse
import os
import signal
import sys

import ufora.BackendGateway.BackendGatewayService as BackendGatewayService
import ufora.networking.ChannelListener as ChannelListener
import ufora.native.CallbackScheduler as CallbackScheduler

def createArgumentParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p',
                        '--port',
                        type=int,
                        default=os.getenv("UFORA_GATEWAY_BASE_PORT", 30008),
                        help="The network port to listen on. Default: %(default)s")

    parser.add_argument('-s',
                        '--store-address',
                        default=os.getenv("UFORA_GATEWAY_STORE_ADDRESS", "localhost:30002"),
                        help=("The address and port of the Ufora store service. "
                              "Default: %(default)s"))

    parser.add_argument('-c',
                        '--cluster-name',
                        default=os.getenv("UFORA_GATEWAY_CLUSTER_NAME", "(default)"),
                        help=("The name of the cluster this gateway is connected to. "
                              "Default: %(default)s"))
    return parser


def createService(args):
    callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()
    callbackScheduler = callbackSchedulerFactory.createScheduler('ufora-gateway', 1)
    channelListener = ChannelListener.SocketListener(args.port)
    return BackendGatewayService.BackendGatewayService(callbackScheduler,
                                                       channelListener,
                                                       args.store_address)


def main(args):
    print "ufora-gateway starting"
    worker = createService(args)
    worker.startService(None)

    def signal_handler(sig, _):
        signal_name = '(unknown)'
        if sig == signal.SIGINT:
            signal_name = 'SIGINT'
        elif sig == signal.SIGTERM:
            signal_name = 'SIGTERM'

        print 'Received ', signal_name, 'signal. Exiting.'

        worker.stopService()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print "Press Ctrl+C to exit."
    signal.pause()


if __name__ == "__main__":
    main(createArgumentParser().parse_args())

