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
import string
import sys
import os
import subprocess

if len(sys.argv) < 2:
    sys.exit(0)

args = list(sys.argv)


for ix in range(1, len(args)):
	fname = args[ix]
	suffix = os.path.splitext(fname)[1]

	if suffix in [".cpp", ".hpp", ".cppml", ".hppml"]:
		args = args[:1] + [fname] + args[1:ix] + args[ix+1:]
		args = [x for x in args if x != '-atomic_ops']

		if suffix == ".cppml" or suffix == ".cpp":
			srcType = "c++"
		elif suffix == ".hppml" or suffix == ".hpp":
			srcType = "c++-header"

		outOptionIx = -1
		for i in range(len(args)):
			if args[i][:2] == "-o":
				outOptionIx = i

		if outOptionIx >= 0:
			if args[outOptionIx] == "-o":
				outNameIx = outOptionIx + 1
			else:
				outNameIx = outOptionIx

		preProcArgs = [x for x in list(args) if x != '-atomic_ops']

		if outOptionIx >= 0:
			preProcArgs = preProcArgs[:outOptionIx] + preProcArgs[outNameIx + 1:]

		preprocessRes = subprocess.Popen("gcc-4.6 -E -x " + srcType + (" -include atomic_ops.h " if '-atomic_ops' in sys.argv else ' ') + string.join(preProcArgs[1:], " "), stdout=subprocess.PIPE, stderr = subprocess.PIPE, close_fds = True, shell=True)
		preprocessedOut, preprocessedErr = preprocessRes.communicate()

                if preprocessRes.wait() > 0:
                        sys.stderr.write(preprocessedErr)
                        sys.exit(preprocessRes.poll())

                sys.stderr.write(preprocessedErr)

                cppmlProc = subprocess.Popen("cppml - " + (" -atomic_ops " if '-atomic_ops' in sys.argv else ' '), stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE, shell=True, close_fds = True)
		cppmlOut, cppmlErr = cppmlProc.communicate(preprocessedOut)

                sys.stderr.write(cppmlErr)

		if cppmlProc.wait() > 0:
                        sys.stderr.write(cppmlErr)
			sys.exit(cppmlProc.poll())

                finalProc = subprocess.Popen("gcc -x " + srcType + " - " + string.join(args[2:], " "), stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE, shell=True, close_fds = True)
		finalOut, finalErr = finalProc.communicate(cppmlOut)

                sys.stderr.write(finalErr)
                sys.stdout.write(finalOut)

		if finalProc.wait() > 0:
                        sys.stderr.write(finalErr)
			sys.exit(finalProc.poll())
		sys.exit(0)


args[0] = "gcc"
if sys.platform == "darwin":
	args = args + ["-lstdc++"]

cmdLine = string.join(args, " ")
f = os.popen(cmdLine)
f.read()

rv = f.close()
sys.exit(0 if rv is None else 1)

