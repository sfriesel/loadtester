#!/bin/bash
set -e
d="$(date +%s)"
time ./loadtester.py "$@" > results-$d.txt
gnuplot <<EOF
set terminal png size 1600,900;
set output './results-$d.png';
set palette model RGB defined ( 0 'red', 1 'green' );
set cbrange [0:1]
set grid x y
set logscale y
set ytics nomirror
set ylabel "session response time [s]"
set y2tics nomirror
set y2label "new sessions [1/s]"
set tics out
set autoscale  y
set autoscale y2
plot './results-$d.txt' using 1:(abs(\$2-\$1)):(\$2-\$1):(0):3 with vectors palette title 'session response time [s]', './results-$d.txt' using (floor(\$1)):(1) smooth freq with linespoints lt rgb "blue" axes x1y2 title 'new sessions [1/s]'
EOF
cp results-$d.png results.png
