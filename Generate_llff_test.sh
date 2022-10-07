#!/bin/bash
f=$1

for i in $(seq 2 10); 
do
    # implement your logic here
    echo $f
    python3 train.py --config $f --NBV_route 1 --render_test 1 --llff_hold $i

done