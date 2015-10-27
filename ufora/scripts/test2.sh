#!/bin/bash

rm out* -rf
rm log* -rf
rm nose* -rf

testRepeater.py 0 $@ --baseport 20000  --datarootsubdir test0 &
testRepeater.py 1 $@ --baseport 20100  --datarootsubdir test1 &
