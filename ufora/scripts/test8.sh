#!/bin/bash

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

