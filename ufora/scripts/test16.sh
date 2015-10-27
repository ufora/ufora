#!/bin/bash

rm out* -rf
rm log* -rf
rm nose* -rf

testRepeater.py 0 $@ --baseport 20000  --datarootsubdir test0 &
testRepeater.py 1 $@ --baseport 20100  --datarootsubdir test1 &
testRepeater.py 2 $@ --baseport 20200  --datarootsubdir test2 &
testRepeater.py 3 $@ --baseport 20300  --datarootsubdir test3 &
testRepeater.py 4 $@ --baseport 20400  --datarootsubdir test4 &
testRepeater.py 5 $@ --baseport 20500  --datarootsubdir test5 &
testRepeater.py 6 $@ --baseport 20600  --datarootsubdir test6 &
testRepeater.py 7 $@ --baseport 20700  --datarootsubdir test7 &
testRepeater.py 8 $@ --baseport 20800  --datarootsubdir test8 &
testRepeater.py 9 $@ --baseport 20900  --datarootsubdir test9 &
testRepeater.py 10 $@ --baseport 21000  --datarootsubdir test10 &
testRepeater.py 11 $@ --baseport 21100  --datarootsubdir test11 &
testRepeater.py 12 $@ --baseport 21200  --datarootsubdir test12 &
testRepeater.py 13 $@ --baseport 21300  --datarootsubdir test13 &
testRepeater.py 14 $@ --baseport 21400  --datarootsubdir test14 &
testRepeater.py 15 $@ --baseport 21500  --datarootsubdir test15 &

