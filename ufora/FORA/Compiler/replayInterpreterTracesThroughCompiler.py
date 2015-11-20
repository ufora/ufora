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

import ufora.FORA.python.Runtime as Runtime
import ufora.config.Setup as Setup
import time
import sys

def main(argv):
	t0 = time.time()

	Runtime.initialize(Setup.defaultSetup())
	
	runtime = Runtime.getMainRuntime()
	handler = runtime.getInterpreterTraceHandler()

	handler.replayTracesFromFile(argv[1])

	print "took ", time.time() - t0

if __name__ == "__main__":
	main(sys.argv)



