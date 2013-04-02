#!/bin/bash
set -e
d="$(date +%s)"
time ./loadtester.py "$@" > results-$d.txt
bash ./plot-sessions.sh results-$d.txt
cp results-$d.png
