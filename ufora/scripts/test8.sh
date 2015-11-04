#!/bin/bash

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

rm out* -rf
rm log* -rf
rm nose* -rf

testRepeater.py 0 $@ --baseport 20000  --datarootsubdir test0  --stack-logfile-path=stack0 &
testRepeater.py 1 $@ --baseport 20100  --datarootsubdir test1  --stack-logfile-path=stack1 &
testRepeater.py 2 $@ --baseport 20200  --datarootsubdir test2  --stack-logfile-path=stack2 &
testRepeater.py 3 $@ --baseport 20300  --datarootsubdir test3  --stack-logfile-path=stack3 &
testRepeater.py 4 $@ --baseport 20400  --datarootsubdir test4  --stack-logfile-path=stack4 &
testRepeater.py 5 $@ --baseport 20500  --datarootsubdir test5  --stack-logfile-path=stack5 &
testRepeater.py 6 $@ --baseport 20600  --datarootsubdir test6  --stack-logfile-path=stack6 &
testRepeater.py 7 $@ --baseport 20700  --datarootsubdir test7  --stack-logfile-path=stack7 &

