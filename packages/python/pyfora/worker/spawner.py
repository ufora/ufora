#!/usr/bin/env python

#   Copyright 2016 Ufora Inc.
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

"""
Entrypoint for the main out-of-process python loop. 

This process is responsible for spawning the child-process workers that 
Cumulus uses to execute out-of-process python code. We need this spawning
to be done in its own process because once cumulus starts up, forking
becomes very expensive on certain kinds of virtualized hardware. As a result,
we need to fork early, and then fork from that process.

This client listens on a named socket. When it gets a connection it forks
and executes the child code.
"""

import argparse
import sys
import os
import traceback
import logging
import pyfora.worker.Spawner as Spawner

def initLogging():
    logging.getLogger().setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(
        logging.Formatter(
            '%(asctime)s %(levelname)s %(filename)s:%(lineno)s@%(funcName)s %(name)s - %(message)s'
            )
        )
    logging.getLogger().addHandler(ch)


def createArgumentParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('socket_dir', help="Path to the named socket directory")
    parser.add_argument('socket_name', help="Base name to get socket assignments")
    parser.add_argument('--max_processes', help="Maximum number of processes", default=None, required=False, type=int)
    return parser

def main(argv):
    initLogging()

    args = createArgumentParser().parse_args(argv)
    
    logging.info("listening on %s/%s", args.socket_dir, args.socket_name)

    if args.max_processes is not None:
        logging.info("Maximum number of workers is %s", args.max_processes)

    try:
        listener = Spawner.Spawner(args.socket_dir, args.socket_name, args.max_processes, True)
        listener.listen()
        listener.teardown()
    except:
        logging.error("unknown exception in pyfora worker process spawner:\n%s", traceback.format_exc())
        sys.stdout.flush()
        sys.stderr.flush()

        try:
            listener.clearPath()
        except:
            pass

        return 1

    return 0



if __name__ == "__main__":
    os._exit(main(sys.argv[1:]))

