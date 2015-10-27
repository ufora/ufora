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

import sys

colorCodes = ['\033[1;%sm' % x for x in [93, 96, 92, 91]]

def main(argv):
    def colorize(l):
        ix = 0
        
        for a in argv[2:]:
            l = l.replace(a, "  <<<<  " + a + "  >>>>  ")
            ix += 1

        return l

    def contains(l):
        for a in argv[2:]:
            if a[:1] == "-" and a[1:] in l:
                return False

        for a in argv[2:]:
            if a[:1] == "+" and a[1:] not in l:
                return False

        for a in argv[2:]:
            if a[:1] != "-" and a[:1] != "+" and a in l:
                return True
        
        return False

    hasOne = False

    lineNumber = 0

    curBlock = []

    for line in open(argv[1],"r"):
        lineNumber += 1

        if line[0] in (' ', '\t') or not curBlock:
            curBlock.append((lineNumber, line.rstrip()))
        else:
            #found one - dump it
            if contains("\n".join([x[1] for x in curBlock])):
                for ln, l in curBlock:
                    print "%7d " % ln, colorize(l.rstrip())

            curBlock = []
            
            curBlock.append((lineNumber, line.rstrip()))


    if contains("\n".join([x[1] for x in curBlock])):
        for lineNumber, line in curBlock:
            print "%7d " % lineNumber, colorize(line.rstrip())
            

if __name__ == "__main__":
    sys.exit(main(sys.argv))
