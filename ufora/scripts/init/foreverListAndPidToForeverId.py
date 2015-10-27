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

#take the output of 'forever --list' from stdin, and a pid on the command line
#and print the forever id to standard out.

import sys
import os

def offsetsFromHeaders(headers, headerToFind):
	lowIndex = headers.find(headerToFind)
	highIndex = lowIndex
	while headers[highIndex] != ' ':
		highIndex += 1

	while headers[highIndex] == ' ':
		highIndex += 1
	return lowIndex, highIndex

def extractForeverId(line):
	index = line.find('[')
	index2 = line.find(']', index)

	return line[index+1:index2]

def main(argv):
	if len(argv) != 3 or argv[2] not in ('id', 'uptime'):
		print >> sys.stderr, "Usage: forever list --plain | foreverListAndPidToForeverId <pid> [id|uptime]"
		return 1

	#the first should be 'info:    Forever processes running'
	firstLine = sys.stdin.readline()
	assert "processes running" in firstLine

	if 'No forever processes running' in firstLine:
		return 0

	#the second line should have headers. These are lined up with the lines of the file
	headers = sys.stdin.readline()

	#search for the character offsets of 'pid' and 'uptime'
	pidOffsets = offsetsFromHeaders(headers, "pid")
	uptimeOffsets = offsetsFromHeaders(headers, "uptime")

	foreverId = None
	for line in sys.stdin.readlines():
		pidForLine = line[pidOffsets[0]:pidOffsets[1]].strip()

		if pidForLine == sys.argv[1]:
			if foreverId is None:
				foreverId = extractForeverId(line)
				uptime = line[uptimeOffsets[0]:uptimeOffsets[1]]
			else:
				print >> sys.stderr, "Pid showed up multiple times in the forever output"
				return 1

	if foreverId is None:
		return 1

	if argv[2] == 'id':
		print foreverId
	else:
		assert argv[2] == 'uptime'
		print uptime

	return 0

if __name__ == "__main__":
	sys.exit(main(sys.argv))
