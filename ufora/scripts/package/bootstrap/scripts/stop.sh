#!/bin/bash

# Stops all Ufora services
ps aux | grep "ufora\|forever" | grep -v grep | awk '{print $2}' | xargs kill -9
