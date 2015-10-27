#!/bin/bash

forever stopall
killexp simulate_cluster.py

rm -rf ~/.bsa
mkdir ~/.bsa

python ufora/test/simulate_cluster.py --logging=info >simulation_log.txt 2>simulation_err.txt &



