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
import socket
import sys

import ufora.config.Config as Config
import ufora.config.Setup as Setup
import ufora.cumulus.distributed.CumulusService as CumulusService
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.distributed.SharedState.Connections.TcpChannelFactory as TcpChannelFactory
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.native.Cumulus as CumulusNative
from ufora.networking.MultiChannelListener import MultiChannelListener

def get_own_ip():
    return socket.gethostbyname(socket.getfqdn())

def createArgumentParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p',
                        '--base-port',
                        type=int,
                        default=os.getenv("UFORA_WORKER_BASE_PORT", 30009),
                        help=("The lower of two consecutive port numbers used by ufora-worker. "
                              "Default: %(default)s"))

    parser.add_argument('-a',
                        '--own-address',
                        default=os.getenv("UFORA_WORKER_OWN_ADDRESS", get_own_ip()),
                        help=("The IP address that this worker should bind to. "
                              "Default: %(default)s"))

    parser.add_argument('-s',
                        '--store-address',
                        default=os.getenv("UFORA_WORKER_STORE_ADDRESS", "localhost:30002"),
                        help=("The address and port of the Ufora store service. "
                              "Default: %(default)s"))

    return parser


def createEventHandler(events_dir, callback_scheduler):
    if not os.path.isdir(events_dir):
        os.makedirs(events_dir)
    return CumulusNative.CumulusWorkerWriteToDiskEventHandler(
        callback_scheduler,
        os.path.join(events_dir, "ufora-worker-events.%s.log" % os.getpid())
        )


def createService(args):
    callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()
    callbackScheduler = callbackSchedulerFactory.createScheduler('ufora-worker', 1)
    channelListener = MultiChannelListener(callbackScheduler,
                                           [args.base_port, args.base_port + 1])

    store_host, store_port = args.store_address.split(':')
    sharedStateViewFactory = ViewFactory.ViewFactory.TcpViewFactory(
        callbackSchedulerFactory.createScheduler('SharedState', 1),
        store_host,
        int(store_port)
        )

    channelFactory = TcpChannelFactory.TcpStringChannelFactory(callbackScheduler)

    diagnostics_dir = os.getenv("UFORA_WORKER_DIAGNOSTICS_DIR")
    eventHandler = diagnostics_dir and createEventHandler(
        diagnostics_dir,
        callbackSchedulerFactory.createScheduler("ufora-worker-event-handler", 1)
        )

    return CumulusService.CumulusService(
        args.own_address,
        channelListener,
        channelFactory,
        eventHandler,
        callbackScheduler,
        diagnostics_dir,
        Setup.config(),
        viewFactory=sharedStateViewFactory
        )

def defaultSetup():
    return Setup.Setup(Config.Config({}))

def main(args):
    print "ufora-worker starting"
    with Setup.PushSetup(defaultSetup()):
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

