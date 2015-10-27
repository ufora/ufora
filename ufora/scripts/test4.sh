#!/bin/bash

rm out* -rf
rm log* -rf
rm nose* -rf

testRepeater.py 0 $@ --baseport 20000  --datarootsubdir test0 --stack-logfile-path=stack0 &
testRepeater.py 1 $@ --baseport 20100  --datarootsubdir test1 --stack-logfile-path=stack1 &
testRepeater.py 2 $@ --baseport 20200  --datarootsubdir test2 --stack-logfile-path=stack2 &
testRepeater.py 3 $@ --baseport 20300  --datarootsubdir test3 --stack-logfile-path=stack3 &
