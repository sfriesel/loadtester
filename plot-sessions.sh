gnuplot <<EOF
set terminal png size 1600,900;
set output '$1.png';
set palette model RGB defined ( 0 'red', 1 'green' );
set cbrange [0:1]
set grid x y
set xlabel 'wallclock time [s]'
set logscale y
set ytics add (0.2,0.3,0.4,0.5,0.6,0.8,1.2,1.5,2,3,4,5,6,8,12,15,20,30,40,50,60,80) nomirror
set ylabel "session response time [s]"
set y2tics nomirror
set y2label "new sessions [1/s]"
set tics out
set autoscale  y
set autoscale y2
plot "$1" using 1:(abs(\$2-\$1)):(\$2-\$1):(0):3 with vectors palette title 'session response time [s]', "$1" using (floor(\$1)):(1) smooth freq with linespoints lt rgb "blue" axes x1y2 title 'new sessions [1/s]'
EOF

