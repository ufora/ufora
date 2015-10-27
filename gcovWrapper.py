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

#!/usr/bin/env python
# encoding: utf-8

""" This script is used to wrap the code coverage tool gcov.

    It exists in order to work around a bug in the tool which causes
    it to peg the CPU at 100% indefinitely when processing our source code.
    This script strips away the command switches that cause that behavior.
"""

import sys
import subprocess

argv = [arg for arg in sys.argv[1:] if arg != '-a' and arg != '-b']
command = 'gcov ' + ' '.join(argv)
if subprocess.Popen(command, shell=True).wait():
    raise SystemExit(1)

sys.exit(0)

